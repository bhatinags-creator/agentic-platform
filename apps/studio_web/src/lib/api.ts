import type {
  AgentDefinition,
  AgentDraft,
  AgentInteractionResult,
  AgentManifest,
  AgentTestCasePayload,
  AgentTestRunResult,
  ConfiguredModelProfile,
  PromptRecord,
  RiskClass,
  ToolDefinition,
  ToolImplementationType
} from "../types";

export interface ApiContext {
  apiKey?: string;
}

const DEFAULT_WORKSPACE_ID = "default";

interface ApiErrorPayload {
  detail?: unknown;
}

function formatApiErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const record = item as { loc?: unknown[]; msg?: unknown };
          const location = Array.isArray(record.loc) ? record.loc.join(".") : "";
          const message = typeof record.msg === "string" ? record.msg : JSON.stringify(item);
          return location ? `${location}: ${message}` : message;
        }
        return String(item);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return "";
}

async function request<T>(path: string, context: ApiContext, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  headers.set("X-Tenant-ID", DEFAULT_WORKSPACE_ID);
  if (context.apiKey) {
    headers.set("X-API-Key", context.apiKey);
  }

  const response = await fetch(path, { ...init, headers });
  const raw = await response.text();
  const payload = raw ? JSON.parse(raw) : undefined;
  if (!response.ok) {
    const errorPayload = payload as ApiErrorPayload | undefined;
    throw new Error(formatApiErrorDetail(errorPayload?.detail) || response.statusText);
  }
  return payload as T;
}

export async function listAgents(context: ApiContext): Promise<AgentDefinition[]> {
  const data = await request<{ agents: AgentDefinition[] }>("/agents", context);
  return data.agents;
}

export async function createAgent(
  context: ApiContext,
  payload: { name: string; owner: string; risk_class: RiskClass }
): Promise<AgentDefinition> {
  const data = await request<{ agent: AgentDefinition }>("/agents", context, {
    method: "POST",
    body: JSON.stringify(payload)
  });
  return data.agent;
}

export async function listDrafts(context: ApiContext): Promise<AgentDraft[]> {
  const data = await request<{ drafts: AgentDraft[] }>("/studio/agent-drafts", context);
  return data.drafts;
}

export async function createDraft(
  context: ApiContext,
  payload: { name: string; owner: string; risk_class: RiskClass; manifest: AgentManifest }
): Promise<AgentDraft> {
  const data = await request<{ draft: AgentDraft }>("/studio/agent-drafts", context, {
    method: "POST",
    body: JSON.stringify(payload)
  });
  return data.draft;
}

export async function updateDraft(
  context: ApiContext,
  draftId: string,
  payload: { name: string; owner: string; risk_class: RiskClass; manifest: AgentManifest }
): Promise<AgentDraft> {
  const data = await request<{ draft: AgentDraft }>(`/studio/agent-drafts/${draftId}`, context, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
  return data.draft;
}

export async function validateDraft(context: ApiContext, draftId: string): Promise<{ valid: boolean; errors: string[] }> {
  const data = await request<{ validation: { valid: boolean; errors: string[] } }>(
    `/studio/agent-drafts/${draftId}/validate`,
    context,
    { method: "POST" }
  );
  return data.validation;
}

export async function publishDraft(context: ApiContext, draftId: string): Promise<void> {
  await request(`/studio/agent-drafts/${draftId}/publish`, context, { method: "POST" });
}

export async function runDraftTests(
  context: ApiContext,
  draftId: string,
  testCases: AgentTestCasePayload[]
): Promise<AgentTestRunResult> {
  const data = await request<{ result: AgentTestRunResult }>(
    `/studio/agent-drafts/${draftId}/test-runs`,
    context,
    {
      method: "POST",
      body: JSON.stringify({ test_cases: testCases })
    }
  );
  return data.result;
}

export async function invokeDraftAgent(
  context: ApiContext,
  draftId: string,
  query: string
): Promise<AgentInteractionResult> {
  const data = await request<{ interaction: AgentInteractionResult }>(
    `/studio/agent-drafts/${draftId}/interactions`,
    context,
    {
      method: "POST",
      body: JSON.stringify({ query })
    }
  );
  return data.interaction;
}

export async function listDraftInteractions(
  context: ApiContext,
  draftId: string
): Promise<AgentInteractionResult[]> {
  const data = await request<{ interactions: AgentInteractionResult[] }>(
    `/studio/agent-drafts/${draftId}/interactions`,
    context
  );
  return data.interactions;
}

interface ModelProfileRecord {
  profile_id: string;
  display_name: string;
  provider: string;
  model: string;
  api_key?: string | null;
}

function toConfiguredModelProfile(record: ModelProfileRecord): ConfiguredModelProfile {
  return {
    profileId: record.profile_id,
    displayName: record.display_name,
    provider: record.provider,
    model: record.model,
    apiKey: record.api_key ?? undefined
  };
}

export async function listModelProfiles(context: ApiContext): Promise<ConfiguredModelProfile[]> {
  const data = await request<{ profiles: ModelProfileRecord[] }>("/studio/model-profiles", context);
  return data.profiles.map(toConfiguredModelProfile);
}

export async function saveModelProfile(
  context: ApiContext,
  profile: ConfiguredModelProfile
): Promise<ConfiguredModelProfile> {
  const data = await request<{ profile: ModelProfileRecord }>("/studio/model-profiles", context, {
    method: "POST",
    body: JSON.stringify({
      profile_id: profile.profileId,
      display_name: profile.displayName,
      provider: profile.provider,
      model: profile.model,
      api_key: profile.apiKey ?? null
    })
  });
  return toConfiguredModelProfile(data.profile);
}

export async function deleteModelProfile(context: ApiContext, profileId: string): Promise<void> {
  await request(`/studio/model-profiles/${encodeURIComponent(profileId)}`, context, { method: "DELETE" });
}

export async function listPrompts(context: ApiContext): Promise<PromptRecord[]> {
  const data = await request<{ prompts: PromptRecord[] }>("/studio/prompts", context);
  return data.prompts;
}

export async function createPrompt(
  context: ApiContext,
  payload: { name: string; owner: string; version: string; template_text: string; description?: string | null }
): Promise<void> {
  await request("/studio/prompts", context, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function listTools(context: ApiContext): Promise<ToolDefinition[]> {
  const data = await request<{ tools: ToolDefinition[] }>("/studio/tools", context);
  return data.tools;
}

export async function createTool(
  context: ApiContext,
  payload: {
    name: string;
    description?: string | null;
    implementation_type: ToolImplementationType;
    endpoint_url?: string | null;
    method: string;
    auth_type: string;
    input_schema: Record<string, unknown>;
    output_schema: Record<string, unknown>;
    risk_class: RiskClass;
    allowed_agents: string[];
    allowed_actions: string[];
    timeout_seconds: number;
  }
): Promise<ToolDefinition> {
  const data = await request<{ tool: ToolDefinition }>("/studio/tools", context, {
    method: "POST",
    body: JSON.stringify(payload)
  });
  return data.tool;
}

export async function testTool(
  context: ApiContext,
  toolName: string,
  payload: { agent_id: string; action?: string | null; payload: Record<string, unknown> }
): Promise<unknown> {
  const data = await request<{ result: unknown }>(`/studio/tools/${encodeURIComponent(toolName)}/test`, context, {
    method: "POST",
    body: JSON.stringify(payload)
  });
  return data.result;
}

export async function loadBootstrap(context: ApiContext) {
  const [agents, drafts, prompts, tools] = await Promise.all([
    listAgents(context),
    listDrafts(context),
    listPrompts(context),
    listTools(context)
  ]);
  return { agents, drafts, prompts, tools };
}

