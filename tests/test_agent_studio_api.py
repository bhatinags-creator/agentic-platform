from fastapi.testclient import TestClient

from apps.control_plane_api.main import create_app
from services.agent_registry.service import AgentRegistryService
from services.agent_studio.service import AgentStudioService


def build_client() -> TestClient:
    registry = AgentRegistryService()
    studio = AgentStudioService(registry=registry)
    return TestClient(create_app(registry=registry, studio=studio))


def build_manifest(name: str = "Customer Support Agent", version: str = "1.0.0") -> dict:
    return {
        "id": "agent.customer-support",
        "name": name,
        "version": version,
        "role": "support-specialist",
        "goal": "resolve customer requests with grounded assistance",
        "model": {"provider": "mock", "model": "mock-model"},
    }


def test_create_list_validate_and_publish_agent_studio_draft() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}

    create_response = client.post(
        "/studio/agent-drafts",
        headers=headers,
        json={
            "name": "Customer Support Agent",
            "owner": "support-team",
            "manifest": build_manifest(),
        },
    )
    draft = create_response.json()["draft"]

    list_response = client.get("/studio/agent-drafts", headers=headers)
    validate_response = client.post(
        f"/studio/agent-drafts/{draft['draft_id']}/validate",
        headers=headers,
    )
    publish_response = client.post(
        f"/studio/agent-drafts/{draft['draft_id']}/publish",
        headers=headers,
    )
    agents_response = client.get("/agents", headers=headers)

    assert create_response.status_code == 201
    assert list_response.json()["drafts"][0]["draft_id"] == draft["draft_id"]
    assert validate_response.json()["validation"]["valid"] is True
    assert publish_response.status_code == 201
    assert publish_response.json()["version"]["manifest"]["version"] == "1.0.0"
    assert agents_response.json()["agents"][0]["name"] == "Customer Support Agent"
    assert agents_response.json()["agents"][0]["status"] == "published"


def test_publish_agent_studio_draft_reuses_existing_agent() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}
    client.post(
        "/agents",
        headers=headers,
        json={"name": "Customer Support Agent", "owner": "support-team", "risk_class": "medium"},
    )
    create_response = client.post(
        "/studio/agent-drafts",
        headers=headers,
        json={
            "name": "Customer Support Agent",
            "owner": "support-team",
            "manifest": build_manifest(),
        },
    )
    draft = create_response.json()["draft"]

    publish_response = client.post(
        f"/studio/agent-drafts/{draft['draft_id']}/publish",
        headers=headers,
    )
    agents_response = client.get("/agents", headers=headers)

    assert publish_response.status_code == 201
    assert agents_response.json()["agents"][0]["status"] == "published"
    assert len(agents_response.json()["agents"]) == 1


def test_agent_studio_draft_validation_error_returns_valid_false() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}
    create_response = client.post(
        "/studio/agent-drafts",
        headers=headers,
        json={
            "name": "Draft Name",
            "owner": "support-team",
            "manifest": build_manifest(name="Manifest Name"),
        },
    )
    draft_id = create_response.json()["draft"]["draft_id"]

    response = client.post(f"/studio/agent-drafts/{draft_id}/validate", headers=headers)

    assert response.status_code == 200
    assert response.json()["validation"] == {
        "draft_id": draft_id,
        "valid": False,
        "errors": ["draft name must match manifest name"],
    }


def test_agent_studio_draft_test_run_endpoint() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}
    create_response = client.post(
        "/studio/agent-drafts",
        headers=headers,
        json={
            "name": "Customer Support Agent",
            "owner": "support-team",
            "manifest": build_manifest(),
        },
    )
    draft_id = create_response.json()["draft"]["draft_id"]

    response = client.post(
        f"/studio/agent-drafts/{draft_id}/test-runs",
        headers=headers,
        json={
            "test_cases": [
                {
                    "name": "goal smoke test",
                    "input": {"message": "help"},
                    "expected_contains": "resolve customer requests",
                }
            ]
        },
    )

    assert response.status_code == 201
    assert response.json()["result"]["status"] == "passed"
    assert response.json()["result"]["checked_cases"] == 1


def test_agent_studio_draft_is_tenant_scoped() -> None:
    client = build_client()
    create_response = client.post(
        "/studio/agent-drafts",
        headers={"X-Tenant-ID": "tenant-a"},
        json={
            "name": "Customer Support Agent",
            "owner": "support-team",
            "manifest": build_manifest(),
        },
    )
    draft_id = create_response.json()["draft"]["draft_id"]

    response = client.get(
        f"/studio/agent-drafts/{draft_id}",
        headers={"X-Tenant-ID": "tenant-b"},
    )

    assert response.status_code == 404
