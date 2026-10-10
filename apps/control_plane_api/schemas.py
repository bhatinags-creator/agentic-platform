from pydantic import BaseModel, Field

from platform_common.domain.models import AgentDefinition, AgentManifest, AgentVersion, RiskClass
from services.agent_studio.service import (
    AgentDraft,
    AgentDraftValidationResult,
    AgentInteractionResult,
    AgentTestRunResult,
)


class CreateAgentRequest(BaseModel):
    name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    risk_class: RiskClass = RiskClass.MEDIUM


class AgentResponse(BaseModel):
    agent: AgentDefinition


class AgentListResponse(BaseModel):
    agents: list[AgentDefinition]


class PublishAgentVersionRequest(BaseModel):
    manifest: AgentManifest


class AgentVersionResponse(BaseModel):
    version: AgentVersion


class AgentVersionListResponse(BaseModel):
    versions: list[AgentVersion]


class CreateAgentDraftRequest(BaseModel):
    name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    manifest: AgentManifest
    risk_class: RiskClass = RiskClass.MEDIUM


class UpdateAgentDraftRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    owner: str | None = Field(default=None, min_length=1)
    manifest: AgentManifest | None = None
    risk_class: RiskClass | None = None


class AgentDraftResponse(BaseModel):
    draft: AgentDraft


class AgentDraftListResponse(BaseModel):
    drafts: list[AgentDraft]


class AgentDraftValidationResponse(BaseModel):
    validation: AgentDraftValidationResult


class AgentTestCaseRequest(BaseModel):
    name: str = Field(min_length=1)
    input: dict = Field(default_factory=dict)
    expected_contains: str | None = None


class RunAgentDraftTestsRequest(BaseModel):
    test_cases: list[AgentTestCaseRequest] = Field(default_factory=list)


class AgentTestRunResponse(BaseModel):
    result: AgentTestRunResult


class InvokeAgentDraftRequest(BaseModel):
    query: str = Field(min_length=1)


class AgentInteractionResponse(BaseModel):
    interaction: AgentInteractionResult


class AgentInteractionListResponse(BaseModel):
    interactions: list[AgentInteractionResult]


class SaveModelProfileRequest(BaseModel):
    profile_id: str | None = None
    display_name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key: str | None = None


class ModelProfileResponse(BaseModel):
    profile: object


class ModelProfileListResponse(BaseModel):
    profiles: list[object]



class CreatePromptTemplateRequest(BaseModel):
    name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    version: str = Field(min_length=1)
    template_text: str = Field(min_length=1)
    description: str | None = None


class PromptTemplateVersionResponse(BaseModel):
    template: object
    version: object


class PromptTemplateListResponse(BaseModel):
    prompts: list[dict]


class CreateToolRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    implementation_type: str = "rest"
    endpoint_url: str | None = None
    method: str = "POST"
    auth_type: str = "none"
    input_schema: dict = Field(default_factory=dict)
    output_schema: dict = Field(default_factory=dict)
    risk_class: str = "medium"
    allowed_agents: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=30, ge=1)


class ToolListResponse(BaseModel):
    tools: list[object]


class TestToolRequest(BaseModel):
    agent_id: str = "studio-tool-tester"
    action: str | None = None
    payload: dict = Field(default_factory=dict)


class TestToolResponse(BaseModel):
    result: object


class CreateRuleRequest(BaseModel):
    name: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    decision: str = "human_review"


class RuleListResponse(BaseModel):
    rules: list[object]


class WorkflowNodeRequest(BaseModel):
    node_type: str = Field(min_length=1)
    name: str = Field(min_length=1)
    service_ref: str | None = None
    instruction: str | None = None
    position: int = 0


class SaveWorkflowRequest(BaseModel):
    agent_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    nodes: list[WorkflowNodeRequest] = Field(default_factory=list)
    workflow_id: str | None = None


class WorkflowListResponse(BaseModel):
    workflows: list[object]
