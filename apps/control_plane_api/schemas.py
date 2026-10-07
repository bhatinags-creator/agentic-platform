from pydantic import BaseModel, Field

from platform_common.domain.models import AgentDefinition, AgentManifest, AgentVersion, RiskClass
from services.agent_studio.service import AgentDraft, AgentDraftValidationResult


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
