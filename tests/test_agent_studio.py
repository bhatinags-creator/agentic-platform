import pytest

from platform_common.domain.models import AgentManifest, ModelProfile
from services.agent_registry.service import AgentRegistryService
from services.agent_studio.service import (
    AgentDraftAlreadyPublishedError,
    AgentDraftNotFoundError,
    AgentDraftStatus,
    AgentStudioService,
)


def build_manifest(name: str = "Customer Support Agent", version: str = "1.0.0") -> AgentManifest:
    return AgentManifest(
        id="agent.customer-support",
        name=name,
        version=version,
        role="support-specialist",
        goal="resolve customer requests with grounded assistance",
        model=ModelProfile(provider="mock", model="mock-model"),
    )


def test_agent_studio_creates_validates_and_publishes_draft() -> None:
    registry = AgentRegistryService()
    studio = AgentStudioService(registry=registry)
    draft = studio.create_draft(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="support-team",
        manifest=build_manifest(),
    )

    validation = studio.validate_draft("tenant-a", draft.draft_id)
    version = studio.publish_draft("tenant-a", draft.draft_id)
    published_draft = studio.get_draft("tenant-a", draft.draft_id)

    assert validation.valid is True
    assert version.manifest.name == "Customer Support Agent"
    assert published_draft.status == AgentDraftStatus.PUBLISHED
    assert published_draft.agent_id == version.agent_id
    assert len(registry.list_agents("tenant-a")) == 1


def test_agent_studio_validation_reports_manifest_alignment_errors() -> None:
    studio = AgentStudioService(registry=AgentRegistryService())
    draft = studio.create_draft(
        tenant_id="tenant-a",
        name="Draft Name",
        owner="support-team",
        manifest=build_manifest(name="Manifest Name"),
    )

    validation = studio.validate_draft("tenant-a", draft.draft_id)

    assert validation.valid is False
    assert validation.errors == ["draft name must match manifest name"]


def test_agent_studio_blocks_updates_after_publish() -> None:
    studio = AgentStudioService(registry=AgentRegistryService())
    draft = studio.create_draft(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="support-team",
        manifest=build_manifest(),
    )
    studio.publish_draft("tenant-a", draft.draft_id)

    with pytest.raises(AgentDraftAlreadyPublishedError):
        studio.update_draft(
            tenant_id="tenant-a",
            draft_id=draft.draft_id,
            owner="new-owner",
        )


def test_agent_studio_is_tenant_scoped() -> None:
    studio = AgentStudioService(registry=AgentRegistryService())
    draft = studio.create_draft(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="support-team",
        manifest=build_manifest(),
    )

    with pytest.raises(AgentDraftNotFoundError):
        studio.get_draft("tenant-b", draft.draft_id)


def test_agent_studio_test_harness_passes_expected_case() -> None:
    studio = AgentStudioService(registry=AgentRegistryService())
    draft = studio.create_draft(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="support-team",
        manifest=build_manifest(),
    )

    result = studio.run_test_harness(
        tenant_id="tenant-a",
        draft_id=draft.draft_id,
        test_cases=[
            {
                "name": "goal smoke test",
                "input": {"message": "refund help"},
                "expected_contains": "resolve customer requests",
            }
        ],
    )

    assert result.status == "passed"
    assert result.checked_cases == 1
    assert result.failures == []
