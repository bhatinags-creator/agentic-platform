from platform_common.domain.models import LifecycleStatus
from services.agent_registry.service import AgentRegistryService, DuplicateAgentNameError
from services.agent_registry.sqlite_repository import SQLiteAgentRegistryRepository
from tests.test_agent_registry import build_manifest


def build_service(database_path) -> AgentRegistryService:
    return AgentRegistryService(repository=SQLiteAgentRegistryRepository(database_path))


def test_sqlite_repository_persists_agents_across_service_instances(tmp_path) -> None:
    database_path = tmp_path / "registry.db"
    first_service = build_service(database_path)
    created_agent = first_service.create_agent("tenant-a", "Claims Agent", "claims-team")

    second_service = build_service(database_path)
    loaded_agent = second_service.get_agent("tenant-a", created_agent.agent_id)

    assert loaded_agent.agent_id == created_agent.agent_id
    assert loaded_agent.name == "Claims Agent"
    assert loaded_agent.status == LifecycleStatus.DRAFT


def test_sqlite_repository_persists_versions_across_service_instances(tmp_path) -> None:
    database_path = tmp_path / "registry.db"
    first_service = build_service(database_path)
    created_agent = first_service.create_agent("tenant-a", "Support Agent", "support-team")
    published_version = first_service.publish_version(
        "tenant-a", created_agent.agent_id, build_manifest("2.0.0")
    )

    second_service = build_service(database_path)
    versions = second_service.list_versions("tenant-a", created_agent.agent_id)
    loaded_agent = second_service.get_agent("tenant-a", created_agent.agent_id)

    assert len(versions) == 1
    assert versions[0].version_id == published_version.version_id
    assert versions[0].manifest.version == "2.0.0"
    assert loaded_agent.status == LifecycleStatus.PUBLISHED


def test_sqlite_repository_enforces_duplicate_agent_name_across_restarts(tmp_path) -> None:
    database_path = tmp_path / "registry.db"
    first_service = build_service(database_path)
    first_service.create_agent("tenant-a", "Finance Agent", "finance-team")

    second_service = build_service(database_path)

    try:
        second_service.create_agent("tenant-a", "finance agent", "finance-team")
    except DuplicateAgentNameError:
        pass
    else:
        raise AssertionError("Expected duplicate agent name to be rejected after restart")
