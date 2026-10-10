import { useMemo, useState } from "react";
import { GitCompare, Library, PlayCircle } from "lucide-react";
import { createPrompt, type ApiContext } from "../../lib/api";
import type { PromptRecord } from "../../types";
import { Button, Card, EmptyState, Field, StatusPill, TextArea, TextInput } from "../../components/ui/Primitives";

interface PromptStudioProps {
  context: ApiContext;
  prompts: PromptRecord[];
  onChanged: () => Promise<void>;
}

export function PromptStudio({ context, prompts, onChanged }: PromptStudioProps) {
  const [selectedId, setSelectedId] = useState(prompts[0]?.template.template_id ?? "");
  const selected = useMemo(() => prompts.find((prompt) => prompt.template.template_id === selectedId) ?? prompts[0], [prompts, selectedId]);
  const [form, setForm] = useState({
    name: "",
    owner: "",
    version: "0.1.0",
    description: "",
    templateText: ""
  });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function savePrompt() {
    setError("");
    setMessage("Saving prompt...");
    try {
      await createPrompt(context, { name: form.name, owner: form.owner, version: form.version, description: form.description || null, template_text: form.templateText });
      setMessage("Prompt saved to backend.");
      await onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save prompt.");
      setMessage("");
    }
  }

  const variables = Array.from(form.templateText.matchAll(/{{\s*([a-zA-Z0-9_]+)\s*}}/g)).map((match) => match[1]);
  const totalVersions = prompts.reduce((count, prompt) => count + prompt.versions.length, 0);

  return (
    <div>
      <section className="hero-panel">
        <div>
          <div className="hero-kicker">Prompt Studio</div>
          <div className="hero-title-row">
            <h1 className="hero-title">Manage reusable instructions</h1>
            <StatusPill tone="ok">API backed</StatusPill>
          </div>
          <p className="hero-copy">Create prompt templates and versions that agents can reference. Phase 1 stores templates in the backend and extracts variable placeholders for review.</p>
        </div>
        <div className="hero-actions"><Button variant="primary" onClick={savePrompt}>Save prompt</Button></div>
      </section>

      <section className="metric-strip">
        <Metric label="Templates" value={prompts.length} />
        <Metric label="Versions" value={totalVersions} />
        <Metric label="Detected Variables" value={variables.length} />
        <Metric label="Mode" value="System" />
      </section>

      <section className="prompt-layout">
        <Card title="Prompt Library">
          {prompts.length === 0 ? (
            <EmptyState title="No prompts yet" body="Create your first governed prompt template." />
          ) : (
            <div className="resource-list">
              {prompts.map((prompt) => (
                <button key={prompt.template.template_id} onClick={() => setSelectedId(prompt.template.template_id)} className={`resource-item ${selected?.template.template_id === prompt.template.template_id ? "active" : ""}`}>
                  <div className="resource-title">{prompt.template.name}</div>
                  <div className="resource-meta">{prompt.template.owner} | {prompt.versions.length} version(s)</div>
                </button>
              ))}
            </div>
          )}
        </Card>

        <Card title="Prompt Editor" action={<Button variant="primary" onClick={savePrompt}>Save version</Button>}>
          <div className="editor-grid">
            <Field label="Template name"><TextInput value={form.name} onChange={(event) => update("name", event.target.value)} /></Field>
            <Field label="Owner"><TextInput value={form.owner} onChange={(event) => update("owner", event.target.value)} /></Field>
            <Field label="Version"><TextInput value={form.version} onChange={(event) => update("version", event.target.value)} /></Field>
            <Field label="Description"><TextInput value={form.description} onChange={(event) => update("description", event.target.value)} /></Field>
            <div className="full-span"><Field label="System instruction template"><TextArea value={form.templateText} onChange={(event) => update("templateText", event.target.value)} style={{ minHeight: 330 }} /></Field></div>
          </div>
          {message && <div className="message-ok">{message}</div>}
          {error && <div className="message-error">{error}</div>}
        </Card>

        <div className="resource-list">
          <Card title="Selected Prompt">
            {selected ? (
              <div className="resource-list">
                <div className="check-row"><span>Name</span><strong>{selected.template.name}</strong></div>
                <div className="check-row"><span>Owner</span><span>{selected.template.owner}</span></div>
                <div className="check-row"><span>Status</span><span>{selected.template.status}</span></div>
                <div className="check-row"><span>Versions</span><span>{selected.versions.length}</span></div>
              </div>
            ) : <EmptyState title="Nothing selected" body="Select or create a prompt template." />}
          </Card>
          <Card title="Variable Editor">
            {variables.length === 0 ? <div className="side-note">No variable placeholders detected. Use double-brace variables when needed.</div> : variables.map((variable) => <span key={variable} className="status-pill">{variable}</span>)}
          </Card>
          <Card title="Phase 1 Scope">
            <div className="resource-list side-note">
              <div><Library size={16} /> Template library and versions are functional.</div>
              <div><PlayCircle size={16} /> Prompt testing comes in Agent Testing Studio.</div>
              <div><GitCompare size={16} /> Prompt comparison comes after version APIs expand.</div>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="metric"><div className="metric-label">{label}</div><div className="metric-value">{value}</div></div>;
}
