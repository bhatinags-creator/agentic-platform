export type RiskClass = "low" | "medium" | "high" | "critical";
export type DataClassification = "public" | "internal" | "confidential" | "restricted";
export type LifecycleStatus = "draft" | "validated" | "published" | "deployed" | "deprecated" | "retired";

export interface AgentDefinition {
  agent_id: string;
  name: string;
  owner: string;
  risk_class: RiskClass;
  status: LifecycleStatus;
  created_at: string;
}

export interface ModelProfile {
  provider: string;
  model: string;
  profile_ref?: string | null;
  parameters?: Record<string, unknown>;
}

export interface ResourceRef {
  ref: string;
  version?: string | null;
  required?: boolean;
}

export interface AgentManifest {
  id: string;
  name: string;
  version: string;
  role: string;
  goal: string;
  model: ModelProfile;
  description?: string | null;
  data_classification: DataClassification;
  tools: ResourceRef[];
  knowledge: ResourceRef[];
  policies: ResourceRef[];
  metadata: Record<string, unknown>;
}

export interface AgentDraft {
  draft_id: string;
  name: string;
  owner: string;
  manifest: AgentManifest;
  risk_class: RiskClass;
  status: "draft" | "validated" | "published";
  agent_id?: string | null;
  published_version_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentTestCasePayload {
  name: string;
  input: Record<string, unknown>;
  expected_contains?: string | null;
}

export interface AgentTestRunResult {
  test_run_id: string;
  draft_id: string;
  status: "passed" | "failed";
  checked_cases: number;
  failures: string[];
  created_at: string;
}

export interface AgentInteractionResult {
  interaction_id: string;
  draft_id: string;
  agent_name: string;
  query: string;
  answer: string;
  created_at: string;
}

export interface PromptTemplate {
  template_id: string;
  name: string;
  owner: string;
  description?: string | null;
  status: string;
  created_at: string;
}

export interface PromptVersion {
  version_id: string;
  template_id: string;
  version: string;
  template_text: string;
  variables: string[];
  status: string;
  created_at: string;
}

export interface PromptRecord {
  template: PromptTemplate;
  versions: PromptVersion[];
}

export type ToolImplementationType = "rest" | "openapi" | "website" | "mcp" | "python" | "echo";

export interface ToolDefinition {
  tool_id: string;
  tenant_id: string;
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
  status: string;
  created_at: string;
}

export interface StudioBootstrap {
  agents: AgentDefinition[];
  drafts: AgentDraft[];
  prompts: PromptRecord[];
  tools: ToolDefinition[];
}


export interface ConfiguredModelProfile {
  profileId: string;
  displayName: string;
  provider: string;
  model: string;
  apiKey?: string;
}
