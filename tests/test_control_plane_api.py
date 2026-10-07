from fastapi.testclient import TestClient

from apps.control_plane_api.main import create_app
from services.agent_registry.service import AgentRegistryService


def build_client() -> TestClient:
    return TestClient(create_app(registry=AgentRegistryService()))


def build_manifest(version: str = "0.1.0") -> dict:
    return {
        "id": "agent.customer-support",
        "name": "Customer Support Agent",
        "version": version,
        "role": "support-specialist",
        "goal": "resolve customer requests with grounded assistance",
        "model": {"provider": "mock", "model": "mock-model"},
    }


def test_health_endpoint() -> None:
    client = build_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "control-plane-api"}


def test_create_and_list_agents_are_tenant_scoped() -> None:
    client = build_client()
    tenant_a_headers = {"X-Tenant-ID": "tenant-a"}
    tenant_b_headers = {"X-Tenant-ID": "tenant-b"}

    create_response = client.post(
        "/agents",
        headers=tenant_a_headers,
        json={"name": "Customer Support Agent", "owner": "ai-platform-team"},
    )

    assert create_response.status_code == 201
    created_agent = create_response.json()["agent"]
    assert created_agent["tenant_id"] == "tenant-a"
    assert created_agent["status"] == "draft"

    tenant_a_list = client.get("/agents", headers=tenant_a_headers)
    tenant_b_list = client.get("/agents", headers=tenant_b_headers)

    assert len(tenant_a_list.json()["agents"]) == 1
    assert tenant_b_list.json()["agents"] == []


def test_duplicate_agent_name_returns_conflict() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}
    payload = {"name": "Claims Agent", "owner": "claims-team"}

    first_response = client.post("/agents", headers=headers, json=payload)
    second_response = client.post("/agents", headers=headers, json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_publish_and_list_agent_versions() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}
    agent_response = client.post(
        "/agents",
        headers=headers,
        json={"name": "Customer Support Agent", "owner": "ai-platform-team"},
    )
    agent_id = agent_response.json()["agent"]["agent_id"]

    publish_response = client.post(
        f"/agents/{agent_id}/versions",
        headers=headers,
        json={"manifest": build_manifest("1.0.0")},
    )
    versions_response = client.get(f"/agents/{agent_id}/versions", headers=headers)
    agent_response_after_publish = client.get(f"/agents/{agent_id}", headers=headers)

    assert publish_response.status_code == 201
    published_version = publish_response.json()["version"]
    assert published_version["status"] == "published"
    assert len(published_version["checksum"]) == 64
    assert len(versions_response.json()["versions"]) == 1
    assert agent_response_after_publish.json()["agent"]["status"] == "published"


def test_publish_for_unknown_agent_returns_not_found() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}

    response = client.post(
        "/agents/00000000-0000-0000-0000-000000000001/versions",
        headers=headers,
        json={"manifest": build_manifest()},
    )

    assert response.status_code == 404


def test_deprecate_agent() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}
    agent_response = client.post(
        "/agents",
        headers=headers,
        json={"name": "Research Agent", "owner": "knowledge-team"},
    )
    agent_id = agent_response.json()["agent"]["agent_id"]

    deprecate_response = client.post(f"/agents/{agent_id}/deprecate", headers=headers)

    assert deprecate_response.status_code == 200
    assert deprecate_response.json()["agent"]["status"] == "deprecated"
