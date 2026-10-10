import { useState } from "react";
import { ArrowLeft, FileText, Plus } from "lucide-react";
import { createAgent, createDraft, createTool, listAgents, publishDraft, updateDraft, type ApiContext } from "../../lib/api";
import type { AgentDefinition, AgentDraft, AgentManifest, ConfiguredModelProfile, DataClassification, PromptRecord, RiskClass, ToolDefinition } from "../../types";
import { Button, Card, EmptyState, Field, Select, StatusPill, TextArea, TextInput } from "../../components/ui/Primitives";

interface AgentStudioProps {
  context: ApiContext;
  agents: AgentDefinition[];
  drafts: AgentDraft[];
  prompts: PromptRecord[];
  tools: ToolDefinition[];
  modelProfiles: ConfiguredModelProfile[];
  onChanged: () => Promise<void>;
}

type AgentFormState = {
  name: string;
  owner: string;
  riskClass: RiskClass;
  dataClassification: DataClassification;
  framework: string;
  version: string;
  role: string;
  goal: string;
  modelProfileId: string;
  modelProvider: string;
  modelName: string;
  systemPrompt: string;
  selectedToolNames: string[];
  memoryPolicy: string;
  approvalPolicy: string;
};

function defaultAgentForm(modelProfiles: ConfiguredModelProfile[]): AgentFormState {
  return {
    name: "",
    owner: "",
    riskClass: "medium",
    dataClassification: "internal",
    framework: "langgraph",
    version: "0.1.0",
    role: "",
    goal: "",
    modelProfileId: modelProfiles[0]?.profileId ?? "",
    modelProvider: modelProfiles[0]?.provider ?? "",
    modelName: modelProfiles[0]?.model ?? "",
    systemPrompt: "",
    selectedToolNames: [],
    memoryPolicy: "",
    approvalPolicy: ""
  };
}

export function AgentStudio({ context, agents, drafts, prompts, tools, modelProfiles, onChanged }: AgentStudioProps) {
  const [page, setPage] = useState<"inventory" | "create">("inventory");
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [activeDraftId, setActiveDraftId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"profile" | "prompt" | "runtime">("profile");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState<AgentFormState>(() => defaultAgentForm(modelProfiles));

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function resetForNewAgent() {
    setMessage("");
    setError("");
    setMode("create");
    setActiveDraftId(null);
    setForm(defaultAgentForm(modelProfiles));
    setActiveTab("profile");
    setPage("create");
  }

  function openAgent(agent: AgentDefinition) {
    const draft = latestEditableDraftForAgent(drafts, agent.name);
    const manifest = draft?.manifest;
    const editingPublishedVersion = draft?.status === "published";
    const matchedProfile =
      modelProfiles.find((profile) => profile.profileId === manifest?.model.profile_ref) ??
      modelProfiles.find((profile) => profile.provider === manifest?.model.provider && profile.model === manifest?.model.model) ??
      modelProfiles[0];
    setMessage("");
    setError("");
    setMode("edit");
    setActiveDraftId(editingPublishedVersion ? null : draft?.draft_id ?? null);
    setForm({
      ...defaultAgentForm(modelProfiles),
      name: agent.name,
      owner: agent.owner,
      riskClass: agent.risk_class,
      dataClassification: manifest?.data_classification ?? "internal",
      framework: String(manifest?.metadata?.framework_runtime ?? "langgraph"),
      version: editingPublishedVersion ? nextPatchVersion(manifest?.version ?? "0.1.0") : manifest?.version ?? "0.1.0",
      role: manifest?.role ?? "",
      goal: manifest?.goal ?? "",
      modelProfileId: matchedProfile?.profileId ?? "",
      modelProvider: matchedProfile?.provider ?? manifest?.model.provider ?? "",
      modelName: matchedProfile?.model ?? manifest?.model.model ?? "",
      systemPrompt: manifest?.description ?? "",
      selectedToolNames: manifest?.tools.map((tool) => tool.ref) ?? [],
      memoryPolicy: String(manifest?.metadata?.memory_policy_note ?? "Conversation: 90 days; working memory: runtime only"),
      approvalPolicy: String(manifest?.metadata?.approval_policy_note ?? "Human review required for regulated advice or unsupported claims")
    });
    setActiveTab("profile");
    setPage("create");
  }

  function buildManifest(): AgentManifest {
    return {
      id: `agent.${form.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`,
      name: form.name.trim(),
      version: form.version.trim(),
      role: form.role.trim(),
      goal: form.goal.trim(),
      model: { provider: form.modelProvider, model: form.modelName, profile_ref: form.modelProfileId || null },
      description: form.systemPrompt,
      data_classification: form.dataClassification,
      tools: form.selectedToolNames.map((toolName) => ({ ref: toolName, required: false })),
      knowledge: [],
      policies: [],
      metadata: {
        framework_runtime: form.framework,
        phase: "phase-1",
        memory_policy_note: form.memoryPolicy,
        approval_policy_note: form.approvalPolicy,
        prompt_templates: prompts.map((prompt) => prompt.template.name)
      }
    };
  }

  function validateForm() {
    if (!form.name.trim()) return "Agent name is required.";
    if (!form.owner.trim()) return "Owner is required.";
    if (!form.version.trim()) return "Version is required.";
    if (!form.role.trim()) return "Role is required.";
    if (!form.goal.trim()) return "Objective is required.";
    if (modelProfiles.length === 0 && (!form.modelProvider.trim() || !form.modelName.trim())) return "Configure a model in Settings before saving an agent.";
    if (!form.modelProvider.trim() || !form.modelName.trim()) return "Select a configured model before saving.";
    return "";
  }

  async function findOrCreateAgent(): Promise<AgentDefinition> {
    const normalizedName = form.name.trim().toLowerCase();
    const knownAgent = agents.find((item) => item.name.trim().toLowerCase() === normalizedName);
    if (knownAgent) return knownAgent;

    const currentAgents = await listAgents(context);
    const existingAgent = currentAgents.find((item) => item.name.trim().toLowerCase() === normalizedName);
    if (existingAgent) return existingAgent;

    try {
      return await createAgent(context, {
        name: form.name.trim(),
        owner: form.owner.trim(),
        risk_class: form.riskClass
      });
    } catch (caught) {
      if (caught instanceof Error && caught.message.toLowerCase().includes("already exists")) {
        const refreshedAgents = await listAgents(context);
        const refreshedAgent = refreshedAgents.find((item) => item.name.trim().toLowerCase() === normalizedName);
        if (refreshedAgent) return refreshedAgent;
      }
      throw caught;
    }
  }

  async function saveDraft(): Promise<{ agent: AgentDefinition; draft: AgentDraft }> {
    const agent = await findOrCreateAgent();
    const payload = {
      name: form.name.trim(),
      owner: form.owner.trim(),
      risk_class: form.riskClass,
      manifest: buildManifest()
    };
    const existingDraft = activeDraftId ? drafts.find((draft) => draft.draft_id === activeDraftId) : undefined;
    const draft = existingDraft && existingDraft.status !== "published"
      ? await updateDraft(context, existingDraft.draft_id, payload)
      : await createDraft(context, payload);
    setActiveDraftId(draft.draft_id);
    return { agent, draft };
  }

  async function syncAgentToolMappings(agentId: string) {
    await Promise.all(tools.map((tool) => {
      const shouldAttach = form.selectedToolNames.includes(tool.name);
      const nextAllowedAgents = shouldAttach
        ? Array.from(new Set([...tool.allowed_agents, agentId]))
        : tool.allowed_agents.filter((allowedAgentId) => allowedAgentId !== agentId);
      if (nextAllowedAgents.length === tool.allowed_agents.length && nextAllowedAgents.every((id, index) => id === tool.allowed_agents[index])) {
        return Promise.resolve();
      }
      return createTool(context, {
        name: tool.name,
        description: tool.description ?? null,
        implementation_type: tool.implementation_type,
        endpoint_url: tool.endpoint_url ?? null,
        method: tool.method,
        auth_type: tool.auth_type,
        input_schema: tool.input_schema,
        output_schema: tool.output_schema,
        risk_class: tool.risk_class,
        allowed_agents: nextAllowedAgents,
        allowed_actions: tool.allowed_actions,
        timeout_seconds: tool.timeout_seconds
      });
    }));
  }

  async function runAgentSaveFlow(action: "draft" | "submit") {
    setError("");
    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }
    setMessage(action === "draft" ? "Saving agent draft..." : "Submitting agent...");
    try {
      const { agent, draft } = await saveDraft();
      await syncAgentToolMappings(agent.agent_id);
      if (action === "submit") {
        await publishDraft(context, draft.draft_id);
      }
      setMessage(action === "draft" ? `Agent ${agent.name} saved as draft.` : `Agent ${agent.name} submitted and published.`);
      await onChanged();
      setPage("inventory");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : `Unable to ${action === "draft" ? "save" : "submit"} agent.`);
      setMessage("");
    }
  }

  if (page === "create") {
    return <CreateAgentPage mode={mode} modelProfiles={modelProfiles} tools={tools} activeTab={activeTab} setActiveTab={setActiveTab} form={form} update={update} manifestPreview={JSON.stringify(buildManifest(), null, 2)} message={message} error={error} onCancel={() => setPage("inventory")} onSaveDraft={() => runAgentSaveFlow("draft")} onSubmit={() => runAgentSaveFlow("submit")} />;
  }

  return (
    <div>
      <section className="hero-panel">
        <div>
          <div className="hero-kicker">Agent Studio</div>
          <div className="hero-title-row">
            <h1 className="hero-title">Agent Inventory</h1>
            <StatusPill tone={agents.length > 0 ? "ok" : "warn"}>{agents.length} agent{agents.length === 1 ? "" : "s"}</StatusPill>
          </div>
          <p className="hero-copy">View all agents in one place. Use Create Agent to open a dedicated creation page backed by the control-plane APIs.</p>
        </div>
        <div className="hero-actions"><Button variant="primary" onClick={resetForNewAgent}><Plus size={16} /> Create Agent</Button></div>
      </section>

      <section className="metric-strip">
        <Metric label="Total Agents" value={agents.length} />
        <Metric label="Published" value={agents.filter((agent) => agent.status === "published").length} />
        <Metric label="Draft" value={agents.filter((agent) => agent.status === "draft").length} />
        <Metric label="Prompts" value={prompts.length} />
      </section>

      <Card title="All Agents">
        {agents.length === 0 ? (
          <EmptyState title="No agents created yet" body="Create your first agent to start building and publishing governed agent definitions." />
        ) : (
          <div className="agent-table">
            <div className="agent-table-header"><span>Name</span><span>Owner</span><span>Risk</span><span>Status</span><span>Created</span></div>
            {agents.map((agent) => (
              <button className="agent-table-row agent-table-clickable" key={agent.agent_id} onClick={() => openAgent(agent)}>
                <span className="agent-name">{agent.name}</span>
                <span>{agent.owner}</span>
                <span>{agent.risk_class}</span>
                <span><StatusPill tone={agent.status === "published" ? "ok" : "neutral"}>{agent.status}</StatusPill></span>
                <span>{new Date(agent.created_at).toLocaleString()}</span>
              </button>
            ))}
          </div>
        )}
      </Card>
      {message && <div className="message-ok">{message}</div>}
      {error && <div className="message-error">{error}</div>}
    </div>
  );
}

function CreateAgentPage({ mode, modelProfiles, tools, activeTab, setActiveTab, form, update, manifestPreview, message, error, onCancel, onSaveDraft, onSubmit }: {
  mode: "create" | "edit";
  modelProfiles: ConfiguredModelProfile[];
  tools: ToolDefinition[];
  activeTab: "profile" | "prompt" | "runtime";
  setActiveTab: (tab: "profile" | "prompt" | "runtime") => void;
  form: {
    name: string;
    owner: string;
    modelProfileId: string;
    riskClass: RiskClass;
    dataClassification: DataClassification;
    framework: string;
    version: string;
    role: string;
    goal: string;
    modelProvider: string;
    modelName: string;
    systemPrompt: string;
    selectedToolNames: string[];
    memoryPolicy: string;
    approvalPolicy: string;
  };
  update: <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => void;
  manifestPreview: string;
  message: string;
  error: string;
  onCancel: () => void;
  onSaveDraft: () => void;
  onSubmit: () => void;
}) {
  return (
    <div>
      <section className="hero-panel">
        <div>
          <div className="hero-kicker">Agent Studio</div>
          <div className="hero-title-row"><h1 className="hero-title">{mode === "edit" ? "Edit Agent" : "Create Agent"}</h1><StatusPill>{mode === "edit" ? "Editable draft" : "New draft"}</StatusPill></div>
          <p className="hero-copy">Define the agent profile, prompt, runtime, and governance metadata. Save as draft to keep working, or submit to create and publish the agent version.</p>
        </div>
        <div className="hero-actions"><Button onClick={onCancel}><ArrowLeft size={16} /> Back to Inventory</Button><Button onClick={onSaveDraft}>Save as Draft</Button><Button variant="primary" onClick={onSubmit}>Submit</Button></div>
      </section>

      <section className="create-agent-layout">
        <Card title="Agent Creation Page">
          <div className="tabs">
            <button className={`tab-button ${activeTab === "profile" ? "active" : ""}`} onClick={() => setActiveTab("profile")}>Profile</button>
            <button className={`tab-button ${activeTab === "prompt" ? "active" : ""}`} onClick={() => setActiveTab("prompt")}>Prompt</button>
            <button className={`tab-button ${activeTab === "runtime" ? "active" : ""}`} onClick={() => setActiveTab("runtime")}>Runtime & Governance</button>
          </div>

          {activeTab === "profile" && <div className="editor-grid"><Field label="Agent name"><TextInput value={form.name} onChange={(event) => update("name", event.target.value)} /></Field><Field label="Owner"><TextInput value={form.owner} onChange={(event) => update("owner", event.target.value)} /></Field><Field label="Framework"><Select value={form.framework} onChange={(event) => update("framework", event.target.value)}><option value="langgraph">LangGraph</option><option value="langchain">LangChain</option></Select></Field><Field label="Risk class"><Select value={form.riskClass} onChange={(event) => update("riskClass", event.target.value as RiskClass)}><option>low</option><option>medium</option><option>high</option><option>critical</option></Select></Field><Field label="Data classification"><Select value={form.dataClassification} onChange={(event) => update("dataClassification", event.target.value as DataClassification)}><option>public</option><option>internal</option><option>confidential</option><option>restricted</option></Select></Field><Field label="Version"><TextInput value={form.version} onChange={(event) => update("version", event.target.value)} /></Field><div className="full-span"><Field label="Role"><TextInput value={form.role} onChange={(event) => update("role", event.target.value)} /></Field></div><div className="full-span"><Field label="Objective"><TextArea value={form.goal} onChange={(event) => update("goal", event.target.value)} /></Field></div></div>}

          {activeTab === "prompt" && <div className="editor-grid"><Field label="Configured model"><Select value={form.modelProfileId} onChange={(event) => { const selected = modelProfiles.find((profile) => profile.profileId === event.target.value); update("modelProfileId", event.target.value); if (selected) { update("modelProvider", selected.provider); update("modelName", selected.model); } }}><option value="">Select configured model</option>{modelProfiles.map((profile) => <option key={profile.profileId} value={profile.profileId}>{profile.displayName}</option>)}</Select></Field><Field label="Model provider"><TextInput value={form.modelProvider} readOnly /></Field><Field label="Model name"><TextInput value={form.modelName} readOnly /></Field><div className="full-span"><Field label="System prompt"><TextArea value={form.systemPrompt} onChange={(event) => update("systemPrompt", event.target.value)} style={{ minHeight: 260 }} /></Field></div></div>}

          {activeTab === "runtime" && <div className="editor-grid"><div className="full-span"><Field label="Memory policy"><TextArea value={form.memoryPolicy} onChange={(event) => update("memoryPolicy", event.target.value)} /></Field></div><div className="full-span"><Field label="Human approval policy"><TextArea value={form.approvalPolicy} onChange={(event) => update("approvalPolicy", event.target.value)} /></Field></div><div className="full-span"><ToolSelection tools={tools} selectedToolNames={form.selectedToolNames} onChange={(selectedToolNames) => update("selectedToolNames", selectedToolNames)} /></div><div className="full-span"><div className="side-note">Tool selection is optional. Save the agent without tools, or attach tools now and change the mapping later by editing this agent.</div></div></div>}

          {message && <div className="message-ok">{message}</div>}
          {error && <div className="message-error">{error}</div>}
        </Card>

        <Card title="Manifest Preview" action={<FileText size={17} color="var(--muted)" />}>
          <pre className="code-preview">{manifestPreview}</pre>
        </Card>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="metric"><div className="metric-label">{label}</div><div className="metric-value">{value}</div></div>;
}

function ToolSelection({ tools, selectedToolNames, onChange }: {
  tools: ToolDefinition[];
  selectedToolNames: string[];
  onChange: (selectedToolNames: string[]) => void;
}) {
  function toggleTool(toolName: string) {
    onChange(
      selectedToolNames.includes(toolName)
        ? selectedToolNames.filter((name) => name !== toolName)
        : [...selectedToolNames, toolName]
    );
  }

  if (tools.length === 0) {
    return <EmptyState title="No tools registered" body="Create tools in Tool Studio first, or save this agent without tools." />;
  }

  return (
    <div>
      <div className="field-label" style={{ marginBottom: 8 }}>Agent tools</div>
      <div className="mapping-list">
        {tools.map((tool) => (
          <label className="mapping-row" key={tool.tool_id}>
            <input
              type="checkbox"
              checked={selectedToolNames.includes(tool.name)}
              onChange={() => toggleTool(tool.name)}
            />
            <span>
              <span className="resource-title">{tool.name}</span>
              <span className="resource-meta">{tool.implementation_type} | {tool.method} | {tool.risk_class} risk</span>
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

function latestEditableDraftForAgent(drafts: AgentDraft[], agentName: string): AgentDraft | undefined {
  return drafts
    .filter((draft) => draft.name.trim().toLowerCase() === agentName.trim().toLowerCase())
    .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime())
    .find((draft) => draft.status !== "published") ?? drafts
      .filter((draft) => draft.name.trim().toLowerCase() === agentName.trim().toLowerCase())
      .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime())[0];
}

function nextPatchVersion(version: string): string {
  const parts = version.split(".").map((part) => Number.parseInt(part, 10));
  if (parts.length === 3 && parts.every(Number.isFinite)) {
    return `${parts[0]}.${parts[1]}.${parts[2] + 1}`;
  }
  return `${version}-next`;
}









