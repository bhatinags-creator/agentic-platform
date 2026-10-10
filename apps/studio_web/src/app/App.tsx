import { useCallback, useEffect, useState } from "react";
import { Shell, type StudioRoute } from "../components/layout/Shell";
import { Button, Card, EmptyState, Field, Select, StatusPill, TextInput } from "../components/ui/Primitives";
import { AgentStudio } from "../features/agents/AgentStudio";
import { PromptStudio } from "../features/prompts/PromptStudio";
import { TestingStudio } from "../features/testing/TestingStudio";
import { ToolStudio } from "../features/tools/ToolStudio";
import { ToolTestRunner } from "../features/tools/ToolTestRunner";
import { deleteModelProfile, listModelProfiles, loadBootstrap, saveModelProfile, type ApiContext } from "../lib/api";
import type { ConfiguredModelProfile, StudioBootstrap } from "../types";

const emptyBootstrap: StudioBootstrap = { agents: [], drafts: [], prompts: [], tools: [] };
const defaultModelProfiles: ConfiguredModelProfile[] = [];

export function App() {
  const [route, setRoute] = useState<StudioRoute>("agents");
  const [context, setContext] = useState<ApiContext>({});
  const [modelProfiles, setModelProfiles] = useState<ConfiguredModelProfile[]>(defaultModelProfiles);
  const [data, setData] = useState<StudioBootstrap>(emptyBootstrap);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setData(await loadBootstrap(context));
      setModelProfiles(await listModelProfiles(context));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load Studio data.");
    } finally {
      setLoading(false);
    }
  }, [context]);

  useEffect(() => { void refresh(); }, [refresh]);

  async function updateModelProfiles(next: ConfiguredModelProfile[]) {
    const savedProfiles = await Promise.all(next.map((profile) => saveModelProfile(context, profile)));
    setModelProfiles(savedProfiles);
    const firstKey = next.find((profile) => profile.apiKey)?.apiKey;
    setContext({ apiKey: firstKey || undefined });
  }

  async function removeModelProfile(profileId: string) {
    await deleteModelProfile(context, profileId);
    const next = modelProfiles.filter((profile) => profile.profileId !== profileId);
    setModelProfiles(next);
    const firstKey = next.find((profile) => profile.apiKey)?.apiKey;
    setContext({ apiKey: firstKey || undefined });
  }

  return (
    <Shell route={route} onRouteChange={setRoute} onRefresh={refresh}>
      {(loading || error) && (
        <div style={{ marginBottom: 14, display: "flex", gap: 10, alignItems: "center" }}>
          {loading && <StatusPill>Loading backend records...</StatusPill>}
          {error && <span className="status-pill" style={{ borderColor: "#f0c4c0", background: "var(--bad-soft)", color: "var(--bad)" }}>{error}</span>}
        </div>
      )}
      {route === "agents" && <AgentStudio context={context} agents={data.agents} drafts={data.drafts} prompts={data.prompts} tools={data.tools} modelProfiles={modelProfiles} onChanged={refresh} />}
      {route === "prompts" && <PromptStudio context={context} prompts={data.prompts} onChanged={refresh} />}
      {route === "tools" && <ToolStudio context={context} tools={data.tools} onChanged={refresh} />}
      {route === "tool-runner" && <ToolTestRunner context={context} tools={data.tools} agents={data.agents} />}
      {route === "testing" && <TestingStudio context={context} agents={data.agents} drafts={data.drafts} />}
      {route === "settings" && <SettingsPanel modelProfiles={modelProfiles} onModelProfilesChange={updateModelProfiles} onModelProfileRemove={removeModelProfile} />}
      {!["agents", "prompts", "tools", "tool-runner", "testing", "settings"].includes(route) && <ComingSoon route={route} />}
    </Shell>
  );
}

function SettingsPanel({ modelProfiles, onModelProfilesChange, onModelProfileRemove }: { modelProfiles: ConfiguredModelProfile[]; onModelProfilesChange: (profiles: ConfiguredModelProfile[]) => Promise<void>; onModelProfileRemove: (profileId: string) => Promise<void> }) {
  const [draft, setDraft] = useState({ displayName: "", provider: "OpenAI", model: "", apiKey: "" });

  async function addProfile() {
    if (!draft.displayName.trim() || !draft.model.trim()) return;
    await onModelProfilesChange([
      ...modelProfiles,
      {
        profileId: `${draft.provider}-${draft.model}-${Date.now()}`.toLowerCase().replace(/[^a-z0-9]+/g, "-"),
        displayName: draft.displayName.trim(),
        provider: draft.provider,
        model: draft.model.trim(),
        apiKey: draft.apiKey.trim() || undefined
      }
    ]);
    setDraft({ displayName: "", provider: "OpenAI", model: "", apiKey: "" });
  }

  async function removeProfile(profileId: string) {
    await onModelProfileRemove(profileId);
  }

  return (
    <div>
      <section className="hero-panel">
        <div>
          <div className="hero-kicker">Settings</div>
          <div className="hero-title-row"><h1 className="hero-title">Model Configuration</h1><StatusPill>Local</StatusPill></div>
          <p className="hero-copy">Configure model profiles once, then select them from Agent Creation. Profiles are persisted in the local control-plane database.</p>
        </div>
      </section>
      <section className="create-agent-layout">
        <Card title="Configured Models">
          <div className="resource-list">
            {modelProfiles.map((profile) => (
              <div className="resource-item" key={profile.profileId}>
                <div className="resource-title">{profile.displayName}</div>
                <div className="resource-meta">{profile.provider} | {profile.model} | {profile.apiKey ? "API key configured" : "No API key"}</div>
                <div style={{ marginTop: 10 }}><Button variant="danger" onClick={() => removeProfile(profile.profileId)} disabled={modelProfiles.length === 1}>Remove</Button></div>
              </div>
            ))}
          </div>
        </Card>
        <Card title="Add Model Profile" action={<Button variant="primary" onClick={addProfile}>Add model</Button>}>
          <div className="editor-grid">
            <Field label="Display name"><TextInput value={draft.displayName} onChange={(event) => setDraft({ ...draft, displayName: event.target.value })} placeholder="OpenAI Production" /></Field>
            <Field label="Provider"><Select value={draft.provider} onChange={(event) => setDraft({ ...draft, provider: event.target.value })}><option>OpenAI</option><option>Azure OpenAI</option><option>Anthropic</option><option>Google Gemini</option><option>Local</option></Select></Field>
            <Field label="Model"><TextInput value={draft.model} onChange={(event) => setDraft({ ...draft, model: event.target.value })} placeholder="gpt-4o-mini" /></Field>
            <Field label="API Key"><TextInput type="password" value={draft.apiKey} onChange={(event) => setDraft({ ...draft, apiKey: event.target.value })} placeholder="optional" /></Field>
            <div className="full-span"><div className="side-note">Agent Creation reads provider and model from this configured model list.</div></div>
          </div>
        </Card>
      </section>
    </div>
  );
}

function ComingSoon({ route }: { route: string }) {
  return <div className="placeholder-card"><EmptyState title={`${route} is planned`} body="This module is in the approved architecture, but it is intentionally disabled until backend APIs and tests are implemented." /></div>;
}
