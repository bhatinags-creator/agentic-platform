import pytest

from platform_common.domain.models import AgentManifest, LifecycleStatus, ModelProfile, RiskClass
from services.agent_registry.service import (
    AgentNotFoundError,
    AgentRegistryService,
    DuplicateAgentNameError,
    DuplicateAgentVersionError,
    InMemoryAgentRegistryRepository,
)


def build_manifest(version: str = "0.1.0") -> AgentManifest:
    return AgentManifest(
        id="agent.customer-support",
        name="Customer Support Agent",
        version=version,
        role="support-specialist",
        goal="resolve customer requests with policy grounded assistance",
        model=ModelProfile(provider="mock", model="mock-model"),
    )


def test_create_agent_enforces_unique_name_within_tenant() -> None:
    service = AgentRegistryService()
    service.create_agent(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="ai-platform-team",
    )

    with pytest.raises(DuplicateAgentNameError):
        service.create_agent(
            tenant_id="tenant-a",
            name="customer support agent",
            owner="ai-platform-team",
        )


def test_create_agent_allows_same_name_for_different_tenants() -> None:
    service = AgentRegistryService()
    tenant_a_agent = service.create_agent("tenant-a", "Claims Agent", "claims-team")
    tenant_b_agent = service.create_agent("tenant-b", "Claims Agent", "claims-team")

    assert tenant_a_agent.agent_id != tenant_b_agent.agent_id
    assert len(service.list_agents("tenant-a")) == 1
    assert len(service.list_agents("tenant-b")) == 1


def test_publish_version_validates_agent_and_promotes_lifecycle() -> None:
    repository = InMemoryAgentRegistryRepository()
    service = AgentRegistryService(repository=repository)
    agent = service.create_agent(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="ai-platform-team",
        risk_class=RiskClass.HIGH,
    )

    version = service.publish_version("tenant-a", agent.agent_id, build_manifest())

    assert version.status == LifecycleStatus.PUBLISHED
    assert version.checksum is not None
    assert len(version.checksum) == 64
    assert service.get_agent("tenant-a", agent.agent_id).status == LifecycleStatus.PUBLISHED


def test_publish_version_rejects_duplicate_manifest_version() -> None:
    service = AgentRegistryService()
    agent = service.create_agent("tenant-a", "Customer Support Agent", "ai-platform-team")
    manifest = build_manifest("1.0.0")
    service.publish_version("tenant-a", agent.agent_id, manifest)

    with pytest.raises(DuplicateAgentVersionError):
        service.publish_version("tenant-a", agent.agent_id, manifest)


def test_publish_version_is_tenant_scoped() -> None:
    service = AgentRegistryService()
    agent = service.create_agent("tenant-a", "Customer Support Agent", "ai-platform-team")

    with pytest.raises(AgentNotFoundError):
        service.publish_version("tenant-b", agent.agent_id, build_manifest())


def test_list_versions_requires_agent_to_exist() -> None:
    service = AgentRegistryService()

    with pytest.raises(ValueError):
        service.list_versions("tenant-a", "not-a-uuid")
