import { useMemo, useState } from "react";
import { Play, Wrench } from "lucide-react";
import { Button, Card, EmptyState, Field, Select, StatusPill, TextArea, TextInput } from "../../components/ui/Primitives";
import { testTool, type ApiContext } from "../../lib/api";
import type { AgentDefinition, ToolDefinition } from "../../types";

function parseJsonObject(value: string, label: string): Record<string, unknown> {
  const trimmed = value.trim();
  if (!trimmed) return {};
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error(`${label} must be a JSON object.`);
  }
  return parsed as Record<string, unknown>;
}

function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

export function ToolTestRunner({ context, tools, agents }: {
  context: ApiContext;
  tools: ToolDefinition[];
  agents: AgentDefinition[];
}) {
  const [selectedToolName, setSelectedToolName] = useState(tools[0]?.name ?? "");
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [testResult, setTestResult] = useState("");
  const [runner, setRunner] = useState({
    agentId: agents[0]?.agent_id ?? "studio-tool-tester",
    action: "read",
    payload: "{\n  \"query\": \"sample request\"\n}"
  });

  const selectedTool = useMemo(
    () => tools.find((tool) => tool.name === selectedToolName) ?? tools[0],
    [selectedToolName, tools]
  );

  async function runToolTest() {
    const toolName = selectedTool?.name ?? selectedToolName;
    if (!toolName) {
      setError("Select a tool to test.");
      return;
    }
    setTesting(true);
    setMessage("");
    setError("");
    setTestResult("");
    try {
      const result = await testTool(context, toolName, {
        agent_id: runner.agentId || "studio-tool-tester",
        action: runner.action.trim() || null,
        payload: parseJsonObject(runner.payload, "Test payload")
      });
      setTestResult(formatJson(result));
      setMessage("Tool invocation completed through the Tool Gateway.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to test tool.");
    } finally {
      setTesting(false);
    }
  }

  return (
    <div>
      <section className="hero-panel">
        <div>
          <div className="hero-kicker">Tool Studio</div>
          <div className="hero-title-row">
            <h1 className="hero-title">Tool Test Runner</h1>
            <StatusPill>{tools.length} tools</StatusPill>
          </div>
          <p className="hero-copy">Validate registered tool behavior through the governed Tool Gateway using an agent identity, action, and request payload.</p>
        </div>
      </section>

      <section className="tool-test-runner-layout">
        <Card title="Registered Tool">
          {tools.length === 0 ? (
            <EmptyState title="No tools available" body="Create a tool in Tool Studio before running a tool test." />
          ) : (
            <div className="resource-list">
              <Field label="Tool">
                <Select value={selectedTool?.name ?? ""} onChange={(event) => setSelectedToolName(event.target.value)}>
                  {tools.map((tool) => <option key={tool.tool_id} value={tool.name}>{tool.name}</option>)}
                </Select>
              </Field>
              {selectedTool && (
                <div className="tool-detail-bar">
                  <Wrench size={16} />
                  <div>
                    <div className="resource-title">{selectedTool.name}</div>
                    <div className="resource-meta">{selectedTool.status} | {selectedTool.implementation_type} | {selectedTool.auth_type} auth | {selectedTool.timeout_seconds}s timeout</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>

        <Card title="Invocation Input" action={<Button variant="primary" onClick={runToolTest} disabled={testing || !selectedTool}><Play size={16} /> Run test</Button>}>
          {selectedTool ? (
            <div className="resource-list">
              <Field label="Agent">
                <Select value={runner.agentId} onChange={(event) => setRunner({ ...runner, agentId: event.target.value })}>
                  <option value="studio-tool-tester">Studio tool tester</option>
                  {agents.map((agent) => <option key={agent.agent_id} value={agent.agent_id}>{agent.name}</option>)}
                </Select>
              </Field>
              <Field label="Action"><TextInput value={runner.action} onChange={(event) => setRunner({ ...runner, action: event.target.value })} placeholder="read" /></Field>
              <Field label="Payload"><TextArea value={runner.payload} onChange={(event) => setRunner({ ...runner, payload: event.target.value })} /></Field>
              <div className="side-note">This sends the selected agent id, action, and payload to the backend Tool Gateway. Permission failures are returned as governed denials.</div>
              {message && <div className="message-ok">{message}</div>}
              {error && <div className="message-error">{error}</div>}
            </div>
          ) : (
            <EmptyState title="Select a tool" body="Create or select a registered tool before running a governed invocation test." />
          )}
        </Card>

        <Card title="Gateway Response">
          {testResult ? (
            <pre className="code-preview tool-test-output">{testResult}</pre>
          ) : (
            <EmptyState title="No test run yet" body="Run a tool test to inspect the Tool Gateway response." />
          )}
        </Card>
      </section>
    </div>
  );
}
