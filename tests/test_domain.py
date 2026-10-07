import pytest
from pydantic import ValidationError

from platform_common.domain.models import (
    AgentManifest,
    DataClassification,
    FrameworkType,
    MemoryPolicy,
    ModelProfile,
    ResourceRef,
    RetentionPolicy,
)
from services.memory_governance.service import MemoryGovernanceService


def test_agent_manifest_contract() -> None:
    manifest = AgentManifest(
        id="agent.credit-risk-supervisor",
        name="Credit Risk Supervisor",
        version="0.1.0",
        role="supervisor",
        goal="coordinate credit risk assessment",
        framework=FrameworkType.LANGGRAPH,
        data_classification=DataClassification.CONFIDENTIAL,
        model=ModelProfile(provider="mock", model="mock-model"),
        tools=[ResourceRef(ref="tool.customer-profile-api", version="v1")],
    )
    assert manifest.framework == FrameworkType.LANGGRAPH
    assert manifest.model.provider == "mock"
    assert manifest.tools[0].ref == "tool.customer-profile-api"
    assert manifest.memory.human_decisions == RetentionPolicy.YEARS_7


def test_agent_manifest_rejects_noncanonical_id() -> None:
    with pytest.raises(ValidationError):
        AgentManifest(
            id="agent with spaces",
            name="Bad Agent",
            version="0.1.0",
            role="tester",
            goal="validate",
            model=ModelProfile(provider="mock", model="mock-model"),
        )


def test_memory_retention_defaults() -> None:
    service = MemoryGovernanceService()
    assert service.retention_for("session") == "24h"
    assert service.retention_for("human_decisions") == "7y"


def test_memory_policy_defaults_are_enterprise_safe() -> None:
    policy = MemoryPolicy()
    assert policy.session == RetentionPolicy.HOURS_24
    assert policy.agent_working_memory == RetentionPolicy.RUNTIME_ONLY
    assert policy.semantic_memory == RetentionPolicy.POLICY_CONTROLLED
