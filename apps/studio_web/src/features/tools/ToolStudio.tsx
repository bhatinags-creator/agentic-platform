import { useMemo, useState } from "react";
import { Plus } from "lucide-react";
import { Button, Card, EmptyState, Field, Select, StatusPill, TextArea, TextInput } from "../../components/ui/Primitives";
import { createTool, type ApiContext } from "../../lib/api";
import type { RiskClass, ToolDefinition, ToolImplementationType } from "../../types";

const emptyObjectJson = "{\n  \n}";

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  const trimmed = value.trim();
  if (!trimmed) return {};
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object.`);
  }
  return parsed as Record<string, unknown>;
}

function splitCsv(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

function toolStatusTone(status: string): "neutral" | "ok" | "warn" {
  const normalized = status.toLowerCase();
  if (["active", "published", "validated", "deployed"].includes(normalized)) return "ok";
  if (["deprecated", "retired", "disabled", "inactive"].includes(normalized)) return "warn";
  return "neutral";
}

export function ToolStudio({ context, tools, onChanged }: {
  context: ApiContext;
  tools: ToolDefinition[];
  onChanged: () => Promise<void>;
}) {
  const [selectedToolName, setSelectedToolName] = useState(tools[0]?.name ?? "");
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingToolName, setEditingToolName] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [draft, setDraft] = useState({
    name: "",
    description: "",
    implementationType: "rest" as ToolImplementationType,
    endpointUrl: "",
    method: "POST",
    authType: "none",
    riskClass: "medium" as RiskClass,
    allowedActions: "read",
    timeoutSeconds: 30,
    inputSchema: emptyObjectJson,
    outputSchema: emptyObjectJson
  });

  const selectedTool = useMemo(
    () => tools.find((tool) => tool.name === selectedToolName) ?? tools[0],
    [selectedToolName, tools]
  );

  function openCreateTool() {
    setEditingToolName(null);
    setDraft({
      name: "",
      description: "",
      implementationType: "rest",
      endpointUrl: "",
      method: "POST",
      authType: "none",
      riskClass: "medium",
      allowedActions: "read",
      timeoutSeconds: 30,
      inputSchema: emptyObjectJson,
      outputSchema: emptyObjectJson
    });
    setMessage("");
    setError("");
    setEditorOpen(true);
  }

  function openUpdateTool(tool: ToolDefinition) {
    setSelectedToolName(tool.name);
    setEditingToolName(tool.name);
    setDraft({
      name: tool.name,
      description: tool.description ?? "",
      implementationType: tool.implementation_type,
      endpointUrl: tool.endpoint_url ?? "",
      method: tool.method,
      authType: tool.auth_type,
      riskClass: tool.risk_class,
      allowedActions: tool.allowed_actions.join(", "),
      timeoutSeconds: tool.timeout_seconds,
      inputSchema: formatJson(tool.input_schema),
      outputSchema: formatJson(tool.output_schema)
    });
    setMessage("");
    setError("");
    setEditorOpen(true);
  }

  async function saveTool() {
    setSaving(true);
    setMessage("");
    setError("");
    try {
      if (!draft.name.trim()) throw new Error("Tool name is required.");
      const existingTool = tools.find((tool) => tool.name === draft.name.trim());
      await createTool(context, {
        name: draft.name.trim(),
        description: draft.description.trim() || null,
        implementation_type: draft.implementationType,
        endpoint_url: draft.endpointUrl.trim() || null,
        method: draft.method,
        auth_type: draft.authType,
        input_schema: parseJsonObject(draft.inputSchema, "Input schema"),
        output_schema: parseJsonObject(draft.outputSchema, "Output schema"),
        risk_class: draft.riskClass,
        allowed_agents: existingTool?.allowed_agents ?? [],
        allowed_actions: splitCsv(draft.allowedActions),
        timeout_seconds: draft.timeoutSeconds
      });
      setMessage("Tool saved to the control-plane database.");
      await onChanged();
      setSelectedToolName(draft.name.trim());
      setEditingToolName(draft.name.trim());
      setDraft({
        name: "",
        description: "",
        implementationType: "rest",
        endpointUrl: "",
        method: "POST",
        authType: "none",
        riskClass: "medium",
        allowedActions: "read",
        timeoutSeconds: 30,
        inputSchema: emptyObjectJson,
        outputSchema: emptyObjectJson
      });
      setEditorOpen(false);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save tool.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <section className="hero-panel">
        <div>
          <div className="hero-kicker">Tool Studio</div>
          <div className="hero-title-row">
            <h1 className="hero-title">Tool Registry</h1>
            <StatusPill>{tools.length} tools</StatusPill>
          </div>
          <p className="hero-copy">Register governed tools, define schemas and permissions, then validate invocation behavior through the same Tool Gateway used by agents.</p>
        </div>
      </section>

      <section className="registered-tools-section">
        <Card title="Registered Tools" action={<Button variant="primary" onClick={openCreateTool}><Plus size={16} /> Create Tool</Button>}>
          {tools.length === 0 ? (
            <EmptyState title="No tools registered" body="Create the first tool to make it available for governed agent invocation." />
          ) : (
            <div className="tool-table" role="table" aria-label="Registered tools">
              <div className="tool-table-header" role="row">
                <span>Name</span>
                <span>Type</span>
                <span>Status</span>
                <span>Risk</span>
                <span>Method</span>
                <span>Mappings</span>
                <span>Actions</span>
              </div>
              {tools.map((tool) => (
                <button
                  className={`tool-table-row ${selectedTool?.name === tool.name ? "active" : ""}`}
                  key={tool.tool_id}
                  onClick={() => openUpdateTool(tool)}
                  role="row"
                >
                  <span>
                    <span className="tool-name">{tool.name}</span>
                    {tool.description && <span className="tool-description">{tool.description}</span>}
                  </span>
                  <span>{tool.implementation_type}</span>
                  <span><StatusPill tone={toolStatusTone(tool.status)}>{tool.status}</StatusPill></span>
                  <span>{tool.risk_class}</span>
                  <span>{tool.method}</span>
                  <span>{tool.allowed_agents.length ? `${tool.allowed_agents.length} agent(s)` : "Not mapped"}</span>
                  <span>{tool.allowed_actions.length ? tool.allowed_actions.join(", ") : "All"}</span>
                </button>
              ))}
            </div>
          )}
        </Card>
      </section>

      {editorOpen && (
        <section className="tool-editor-section">
          <Card title={editingToolName ? "Update Tool" : "Create Tool"} action={<Button variant="primary" onClick={saveTool} disabled={saving}><Plus size={16} /> Save tool</Button>}>
            <div className="editor-grid">
              <Field label="Tool name"><TextInput value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} placeholder="crm.lookup" /></Field>
              <Field label="Implementation"><Select value={draft.implementationType} onChange={(event) => setDraft({ ...draft, implementationType: event.target.value as ToolImplementationType })}><option value="rest">REST</option><option value="openapi">OpenAPI</option><option value="website">Website</option><option value="mcp">MCP</option><option value="python">Python</option><option value="echo">Echo</option></Select></Field>
              <Field label="Endpoint URL"><TextInput value={draft.endpointUrl} onChange={(event) => setDraft({ ...draft, endpointUrl: event.target.value })} placeholder="https://api.example.com/search" /></Field>
              <Field label="HTTP method"><Select value={draft.method} onChange={(event) => setDraft({ ...draft, method: event.target.value })}><option>GET</option><option>POST</option><option>PUT</option><option>PATCH</option><option>DELETE</option></Select></Field>
              <Field label="Auth type"><Select value={draft.authType} onChange={(event) => setDraft({ ...draft, authType: event.target.value })}><option value="none">None</option><option value="api_key">API key</option><option value="oauth2">OAuth2</option><option value="mTLS">mTLS</option></Select></Field>
              <Field label="Risk class"><Select value={draft.riskClass} onChange={(event) => setDraft({ ...draft, riskClass: event.target.value as RiskClass })}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option></Select></Field>
              <Field label="Allowed actions"><TextInput value={draft.allowedActions} onChange={(event) => setDraft({ ...draft, allowedActions: event.target.value })} placeholder="read, search" /></Field>
              <Field label="Timeout seconds"><TextInput type="number" min={1} value={draft.timeoutSeconds} onChange={(event) => setDraft({ ...draft, timeoutSeconds: Number(event.target.value || 1) })} /></Field>
              <Field label="Description"><TextInput value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} placeholder="What this tool allows the agent to do" /></Field>
              <Field label="Input schema"><TextArea value={draft.inputSchema} onChange={(event) => setDraft({ ...draft, inputSchema: event.target.value })} /></Field>
              <Field label="Output schema"><TextArea value={draft.outputSchema} onChange={(event) => setDraft({ ...draft, outputSchema: event.target.value })} /></Field>
            </div>
            {message && <div className="message-ok">{message}</div>}
            {error && <div className="message-error">{error}</div>}
          </Card>
        </section>
      )}

      <section className="tool-roadmap-grid">
        <Card title="OpenAPI Import">
          <p className="side-note">Phase 2 defines the registry contract for imported REST operations. The next backend increment will parse an OpenAPI document into individual governed tool definitions.</p>
        </Card>
        <Card title="MCP Registry">
          <p className="side-note">MCP server records will use the same tool permission model so agents can call external capabilities through a centrally governed gateway.</p>
        </Card>
      </section>
    </div>
  );
}
