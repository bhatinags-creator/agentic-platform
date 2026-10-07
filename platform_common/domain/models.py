from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class LifecycleStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class RiskClass(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataClassification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class FrameworkType(StrEnum):
    LANGGRAPH = "langgraph"
    LANGCHAIN = "langchain"
    CREWAI = "crewai"
    AUTOGEN = "autogen"
    SEMANTIC_KERNEL = "semantic_kernel"
    LLAMAINDEX = "llamaindex"
    CUSTOM_PYTHON = "custom_python"


class RetentionPolicy(StrEnum):
    RUNTIME_ONLY = "runtime_only"
    HOURS_24 = "24h"
    DAYS_90 = "90d"
    YEARS_7 = "7y"
    POLICY_CONTROLLED = "policy_controlled"


class ResourceRef(BaseModel):
    """Versioned reference to a platform-managed object.

    Examples: tool.customer-profile-api:v2, skill.customer-verification:v1,
    kb.lending-policy:v3. The core stores references instead of embedding
    framework-specific objects.
    """

    ref: str = Field(min_length=1)
    version: str | None = None
    required: bool = True


class ModelProfile(BaseModel):
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    profile_ref: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    data_classification_allowed: list[DataClassification] = Field(default_factory=list)


class MemoryPolicy(BaseModel):
    session: RetentionPolicy = RetentionPolicy.HOURS_24
    conversation: RetentionPolicy = RetentionPolicy.DAYS_90
    agent_working_memory: RetentionPolicy = RetentionPolicy.RUNTIME_ONLY
    semantic_memory: RetentionPolicy = RetentionPolicy.POLICY_CONTROLLED
    human_decisions: RetentionPolicy = RetentionPolicy.YEARS_7


class ExecutionPolicy(BaseModel):
    max_iterations: int = Field(default=12, ge=1)
    max_depth: int = Field(default=3, ge=1)
    timeout_seconds: int = Field(default=900, ge=1)
    max_cost: float | None = Field(default=None, ge=0)
    max_tokens: int | None = Field(default=None, ge=1)


class HumanApprovalPolicy(BaseModel):
    required: bool = False
    policy_ref: str | None = None
    checkpoint_before_wait: bool = True
    approval_modes: list[str] = Field(default_factory=list)


class ObservabilityPolicy(BaseModel):
    tracing_required: bool = True
    audit_required: bool = True
    capture_prompts: Literal["full", "redacted", "hash_only", "none"] = "hash_only"
    capture_outputs: Literal["full", "redacted", "hash_only", "none"] = "redacted"


class EvaluationPolicy(BaseModel):
    required_eval_suite: str | None = None
    minimum_score: float | None = Field(default=None, ge=0, le=1)
    block_deployment_on_failure: bool = True


class AgentManifest(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    role: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    model: ModelProfile
    description: str | None = None
    framework: FrameworkType = FrameworkType.LANGGRAPH
    data_classification: DataClassification = DataClassification.INTERNAL
    skills: list[ResourceRef] = Field(default_factory=list)
    tools: list[ResourceRef] = Field(default_factory=list)
    knowledge: list[ResourceRef] = Field(default_factory=list)
    policies: list[ResourceRef] = Field(default_factory=list)
    guardrails: list[ResourceRef] = Field(default_factory=list)
    sub_agents: list[ResourceRef] = Field(default_factory=list)
    memory: MemoryPolicy = Field(default_factory=MemoryPolicy)
    execution: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
    human_approval: HumanApprovalPolicy = Field(default_factory=HumanApprovalPolicy)
    observability: ObservabilityPolicy = Field(default_factory=ObservabilityPolicy)
    evaluation: EvaluationPolicy = Field(default_factory=EvaluationPolicy)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def agent_id_must_be_canonical(cls, value: str) -> str:
        if " " in value:
            raise ValueError("agent id must not contain spaces")
        return value


class AgentDefinition(BaseModel):
    agent_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    risk_class: RiskClass = RiskClass.MEDIUM
    status: LifecycleStatus = LifecycleStatus.DRAFT
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentVersion(BaseModel):
    version_id: UUID = Field(default_factory=uuid4)
    agent_id: UUID
    manifest: AgentManifest
    status: LifecycleStatus = LifecycleStatus.DRAFT
    checksum: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRun(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    agent_version: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    input: dict[str, Any]
    status: AgentRunStatus = AgentRunStatus.QUEUED
    output: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PolicyDecision(BaseModel):
    decision_id: UUID = Field(default_factory=uuid4)
    decision: Literal["permit", "deny", "permit_with_constraints"]
    constraints: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None
