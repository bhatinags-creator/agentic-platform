import { useEffect, useMemo, useState } from "react";
import { PlayCircle } from "lucide-react";
import { invokeDraftAgent, listDraftInteractions, type ApiContext } from "../../lib/api";
import type { AgentDefinition, AgentDraft, AgentInteractionResult } from "../../types";
import { Button, Card, EmptyState, Field, Select, StatusPill, TextArea } from "../../components/ui/Primitives";

const MAX_VISIBLE_INTERACTIONS = 5;

interface TestingStudioProps {
  context: ApiContext;
  agents: AgentDefinition[];
  drafts: AgentDraft[];
}

export function TestingStudio({ context, agents, drafts }: TestingStudioProps) {
  const [selectedAgentId, setSelectedAgentId] = useState(agents[0]?.agent_id ?? "");
  const selectedAgent = useMemo(() => agents.find((agent) => agent.agent_id === selectedAgentId) ?? agents[0], [agents, selectedAgentId]);
  const selectedDraft = useMemo(() => latestDraftForAgent(drafts, selectedAgent?.name ?? ""), [drafts, selectedAgent]);
  const [query, setQuery] = useState("");
  const [interactions, setInteractions] = useState<AgentInteractionResult[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadInteractions() {
      if (!selectedDraft) {
        setInteractions([]);
        return;
      }
      try {
        const records = await listDraftInteractions(context, selectedDraft.draft_id);
        setInteractions(latestInteractions(records));
      } catch {
        setInteractions([]);
      }
    }
    void loadInteractions();
  }, [context, selectedDraft]);

  async function runAgent() {
    setError("");
    setMessage("");
    if (!selectedAgent) {
      setError("Create an agent before running it.");
      return;
    }
    if (!selectedDraft) {
      setError("Save or submit the agent once before running it. Testing uses the latest agent draft manifest.");
      return;
    }
    if (!query.trim()) {
      setError("Enter a query for the agent.");
      return;
    }

    setMessage("Invoking agent...");
    try {
      const interaction = await invokeDraftAgent(context, selectedDraft.draft_id, query.trim());
      setInteractions((current) => latestInteractions([...current, interaction]));
      setQuery("");
      setMessage("Agent response received.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to run agent.");
      setMessage("");
    }
  }

  return (
    <div>
      <section className="hero-panel">
        <div>
          <div className="hero-kicker">Testing Studio</div>
          <div className="hero-title-row">
            <h1 className="hero-title">Agent Runner</h1>
            <StatusPill tone="ok">Agent invoked</StatusPill>
          </div>
          <p className="hero-copy">Select a created agent, type a user query, and run it through the saved agent draft manifest.</p>
        </div>
        <div className="hero-actions"><Button variant="primary" onClick={runAgent}><PlayCircle size={16} /> Run Agent</Button></div>
      </section>

      <section className="metric-strip">
        <Metric label="Agents" value={agents.length} />
        <Metric label="Drafts" value={drafts.length} />
        <Metric label="Selected Draft" value={selectedDraft ? selectedDraft.status : "none"} />
        <Metric label="Responses" value={interactions.length} />
      </section>

      <section className="agent-runner-layout">
        <Card title="Agent Query">
          {agents.length === 0 ? (
            <EmptyState title="No agents available" body="Create and save an agent before opening the agent runner." />
          ) : (
            <div className="editor-grid">
              <div className="full-span">
                <Field label="Agent">
                  <Select value={selectedAgent?.agent_id ?? ""} onChange={(event) => setSelectedAgentId(event.target.value)}>
                    {agents.map((agent) => <option key={agent.agent_id} value={agent.agent_id}>{agent.name}</option>)}
                  </Select>
                </Field>
              </div>
              <div className="full-span">
                <Field label="User query">
                  <TextArea value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Ask the agent a question..." style={{ minHeight: 180 }} />
                </Field>
              </div>
              <div className="full-span">
                <Button variant="primary" onClick={runAgent}><PlayCircle size={16} /> Run Agent</Button>
              </div>
            </div>
          )}
          {message && <div className="message-ok">{message}</div>}
          {error && <div className="message-error">{error}</div>}
        </Card>

        <Card title="Agent Conversation">
          {interactions.length === 0 ? (
            <EmptyState title="No response yet" body="Run an agent query to see the response." />
          ) : (
            <div className="chat-transcript">
              {interactions.map((interaction) => (
                <div className="chat-exchange" key={interaction.interaction_id}>
                  <div className="chat-row chat-row-user">
                    <div className="chat-avatar">You</div>
                    <div className="chat-bubble chat-bubble-user">{interaction.query}</div>
                  </div>
                  <div className="chat-row chat-row-agent">
                    <div className="chat-avatar chat-avatar-agent">{agentInitials(interaction.agent_name)}</div>
                    <div className="chat-message">
                      <div className="chat-agent-name">{interaction.agent_name}</div>
                      <div className="chat-answer">{interaction.answer}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </section>
    </div>
  );
}

function latestDraftForAgent(drafts: AgentDraft[], agentName: string): AgentDraft | undefined {
  return drafts
    .filter((draft) => draft.name.trim().toLowerCase() === agentName.trim().toLowerCase())
    .sort((left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime())[0];
}

function Metric({ label, value }: { label: string | number; value: string | number }) {
  return <div className="metric"><div className="metric-label">{label}</div><div className="metric-value">{value}</div></div>;
}

function agentInitials(name: string): string {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
  return initials || "AI";
}

function latestInteractions(interactions: AgentInteractionResult[]): AgentInteractionResult[] {
  return interactions
    .slice()
    .sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime())
    .slice(0, MAX_VISIBLE_INTERACTIONS);
}
