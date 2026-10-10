from types import SimpleNamespace

import pytest

from platform_common.domain.models import AgentManifest, ModelProfile
from services.agent_registry.service import AgentRegistryService
from services.agent_studio.service import (
    AgentDraftAlreadyPublishedError,
    AgentDraftNotFoundError,
    AgentDraftStatus,
    AgentStudioService,
)
from services.agent_studio.sqlite_repository import SQLiteAgentDraftRepository
from services.model_config.service import ModelConfigService


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


def test_agent_studio_publish_reuses_existing_agent_created_from_draft() -> None:
    registry = AgentRegistryService()
    studio = AgentStudioService(registry=registry)
    existing_agent = registry.create_agent(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="support-team",
    )
    draft = studio.create_draft(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="support-team",
        manifest=build_manifest(),
    )

    version = studio.publish_draft("tenant-a", draft.draft_id)
    published_agent = registry.get_agent("tenant-a", existing_agent.agent_id)

    assert version.agent_id == existing_agent.agent_id
    assert published_agent.status == "published"
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


@pytest.mark.anyio
async def test_agent_studio_interaction_runs_runtime_without_prompt_leakage() -> None:
    studio = AgentStudioService(registry=AgentRegistryService())
    draft = studio.create_draft(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="support-team",
        manifest=build_manifest(),
    )

    interaction = await studio.invoke_draft_agent(
        tenant_id="tenant-a",
        draft_id=draft.draft_id,
        query="tell me about credit cards",
    )

    assert "tell me about credit cards" in interaction.answer
    assert "Instruction:" not in interaction.answer
    assert "# Role" not in interaction.answer
    assert draft.manifest.goal not in interaction.answer


@pytest.mark.anyio
async def test_agent_studio_resolves_configured_model_profile_for_runtime(tmp_path) -> None:
    class CapturingRuntime:
        def __init__(self) -> None:
            self.input_payload = {}

        async def start_run(self, **kwargs):
            self.input_payload = kwargs["input_payload"]
            return SimpleNamespace(output={"model": {"output_text": "provider response"}})

    database_path = tmp_path / "agentic_platform.db"
    model_config = ModelConfigService(database_path)
    model_config.save_profile(
        tenant_id="tenant-a",
        profile_id="openai-main",
        display_name="OpenAI Main",
        provider="OpenAI",
        model="gpt-4o-mini",
        api_key="test-key",
    )
    runtime = CapturingRuntime()
    studio = AgentStudioService(
        registry=AgentRegistryService(),
        model_config=model_config,
        runtime=runtime,
    )
    manifest = build_manifest()
    manifest.model.profile_ref = "openai-main"
    draft = studio.create_draft(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="support-team",
        manifest=manifest,
    )

    interaction = await studio.invoke_draft_agent(
        tenant_id="tenant-a",
        draft_id=draft.draft_id,
        query="hello",
    )

    assert interaction.answer == "provider response"
    assert runtime.input_payload["framework_runtime"] == "langgraph"
    assert runtime.input_payload["model_profile"] == {
        "provider": "OpenAI",
        "model": "gpt-4o-mini",
        "profile_ref": "openai-main",
        "parameters": {},
        "data_classification_allowed": [],
        "api_key": "test-key",
    }


@pytest.mark.anyio
async def test_agent_studio_resolves_legacy_manifest_model_by_provider_and_name(tmp_path) -> None:
    class CapturingRuntime:
        def __init__(self) -> None:
            self.input_payload = {}

        async def start_run(self, **kwargs):
            self.input_payload = kwargs["input_payload"]
            return SimpleNamespace(output={"model": {"output_text": "provider response"}})

    database_path = tmp_path / "agentic_platform.db"
    model_config = ModelConfigService(database_path)
    model_config.save_profile(
        tenant_id="tenant-a",
        profile_id="openai-main",
        display_name="OpenAI Main",
        provider="OpenAI",
        model="gpt-4o-mini",
        api_key="test-key",
    )
    runtime = CapturingRuntime()
    studio = AgentStudioService(
        registry=AgentRegistryService(),
        model_config=model_config,
        runtime=runtime,
    )
    manifest = build_manifest()
    manifest.model.provider = "OpenAI"
    manifest.model.model = "gpt-4o-mini"
    draft = studio.create_draft(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="support-team",
        manifest=manifest,
    )

    await studio.invoke_draft_agent(
        tenant_id="tenant-a",
        draft_id=draft.draft_id,
        query="hello",
    )

    assert runtime.input_payload["model_profile"]["profile_ref"] == "openai-main"
    assert runtime.input_payload["model_profile"]["api_key"] == "test-key"


def test_sqlite_agent_studio_repository_persists_drafts_across_service_restarts(tmp_path) -> None:
    database_path = tmp_path / "agentic_platform.db"
    first_studio = AgentStudioService(
        registry=AgentRegistryService(),
        repository=SQLiteAgentDraftRepository(database_path),
    )
    draft = first_studio.create_draft(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="support-team",
        manifest=build_manifest(),
    )

    second_studio = AgentStudioService(
        registry=AgentRegistryService(),
        repository=SQLiteAgentDraftRepository(database_path),
    )
    loaded_draft = second_studio.get_draft("tenant-a", draft.draft_id)

    assert loaded_draft.name == "Customer Support Agent"
    assert loaded_draft.manifest.role == "support-specialist"
    assert second_studio.list_drafts("tenant-a")[0].draft_id == draft.draft_id
