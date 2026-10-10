import pytest

from services.agent_registry.service import AgentRegistryService
from services.agent_studio.service import AgentStudioService
from services.agent_studio.sqlite_repository import SQLiteAgentDraftRepository, SQLiteAgentInteractionRepository
from services.model_config.service import ModelConfigService
from services.prompt_management.service import PromptManagementService, SQLitePromptRepository
from services.studio_assets.service import SQLiteStudioAssetRepository, StudioAssetService
from services.tool_gateway.service import SQLiteToolRepository, ToolRegistryService
from tests.test_agent_studio import build_manifest


def test_model_profiles_persist_across_service_instances(tmp_path) -> None:
    database_path = tmp_path / "agentic_platform.db"
    first = ModelConfigService(database_path)
    saved = first.save_profile(
        tenant_id="tenant-a",
        display_name="OpenAI Production",
        provider="OpenAI",
        model="gpt-test",
        api_key="secret",
    )

    second = ModelConfigService(database_path)

    assert second.list_profiles("tenant-a")[0].profile_id == saved.profile_id
    assert second.list_profiles("tenant-a")[0].model == "gpt-test"


def test_prompt_templates_persist_across_service_instances(tmp_path) -> None:
    database_path = tmp_path / "agentic_platform.db"
    first = PromptManagementService(repository=SQLitePromptRepository(database_path))
    template = first.create_template(tenant_id="tenant-a", name="Support", owner="team")
    first.create_version(
        tenant_id="tenant-a",
        template_id=template.template_id,
        version="1.0.0",
        template_text="Hello {name}",
    )

    second = PromptManagementService(repository=SQLitePromptRepository(database_path))

    assert second.list_templates("tenant-a")[0].name == "Support"
    assert second.list_versions("tenant-a", template.template_id)[0].variables == ["name"]


def test_tools_rules_and_workflows_persist_across_service_instances(tmp_path) -> None:
    database_path = tmp_path / "agentic_platform.db"
    first_tools = ToolRegistryService(repository=SQLiteToolRepository(database_path))
    first_assets = StudioAssetService(repository=SQLiteStudioAssetRepository(database_path))
    first_tools.register_tool(tenant_id="tenant-a", name="crm.lookup", allowed_actions=["read"])
    first_assets.create_rule(tenant_id="tenant-a", name="PII review", condition="contains pii")
    first_assets.save_workflow(
        tenant_id="tenant-a",
        agent_id="agent-1",
        name="Support flow",
        nodes=[{"node_type": "trigger", "name": "Start"}],
    )

    second_tools = ToolRegistryService(repository=SQLiteToolRepository(database_path))
    second_assets = StudioAssetService(repository=SQLiteStudioAssetRepository(database_path))

    assert second_tools.list_tools("tenant-a")[0].name == "crm.lookup"
    assert second_assets.list_rules("tenant-a")[0].name == "PII review"
    assert second_assets.list_workflows("tenant-a", "agent-1")[0].name == "Support flow"


@pytest.mark.anyio
async def test_testing_interactions_persist_across_service_instances(tmp_path) -> None:
    database_path = tmp_path / "agentic_platform.db"
    first = AgentStudioService(
        registry=AgentRegistryService(),
        repository=SQLiteAgentDraftRepository(database_path),
        interaction_repository=SQLiteAgentInteractionRepository(database_path),
    )
    draft = first.create_draft(
        tenant_id="tenant-a",
        name="Customer Support Agent",
        owner="support-team",
        manifest=build_manifest(),
    )
    await first.invoke_draft_agent(tenant_id="tenant-a", draft_id=draft.draft_id, query="How can you help?")

    second = AgentStudioService(
        registry=AgentRegistryService(),
        repository=SQLiteAgentDraftRepository(database_path),
        interaction_repository=SQLiteAgentInteractionRepository(database_path),
    )

    assert second.list_interactions(tenant_id="tenant-a", draft_id=draft.draft_id)[0].query == "How can you help?"
