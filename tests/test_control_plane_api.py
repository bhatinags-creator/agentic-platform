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



def test_local_agent_studio_page_loads() -> None:
    client = build_client()

    response = client.get("/studio")

    assert response.status_code == 200
    assert "Agent Studio" in response.text
    assert "Nexus AI Platform" in response.text
    assert "Agent Blueprint" in response.text
    assert "Agent Definition" in response.text
    assert "Workflow Designer" in response.text
    assert "Prompt Editor" in response.text
    assert "Tools & Rules" in response.text
    assert "refreshManifest" in response.text
    assert "savePrompt" in response.text
    assert "saveTool" in response.text
    assert "saveRule" in response.text
    assert "addNode" in response.text


def test_evaluation_workspace_and_deployment_console_pages_load() -> None:
    client = build_client()

    evaluation_response = client.get("/studio/evaluations")
    deployment_response = client.get("/studio/deployments")

    assert evaluation_response.status_code == 200
    assert "Evaluation Workspace" in evaluation_response.text
    assert deployment_response.status_code == 200
    assert "Deployment Console" in deployment_response.text


def test_optional_api_key_auth_protects_control_plane_api(monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_PLATFORM_API_KEY", "secret")
    client = TestClient(create_app(registry=AgentRegistryService()))

    missing_key_response = client.get("/agents", headers={"X-Tenant-ID": "tenant-a"})
    valid_key_response = client.get(
        "/agents",
        headers={"X-Tenant-ID": "tenant-a", "X-API-Key": "secret"},
    )

    assert missing_key_response.status_code == 401
    assert valid_key_response.status_code == 200


def test_studio_asset_apis_create_and_list_backend_records() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}
    agent_response = client.post(
        "/agents",
        headers=headers,
        json={"name": "Policy Review Agent", "owner": "risk-team"},
    )
    agent_id = agent_response.json()["agent"]["agent_id"]

    prompt_response = client.post(
        "/studio/prompts",
        headers=headers,
        json={
            "name": "policy-review-system",
            "owner": "risk-team",
            "version": "0.1.0",
            "template_text": "Review the policy using approved tools only.",
        },
    )
    tool_response = client.post(
        "/studio/tools",
        headers=headers,
        json={
            "name": "policy.search",
            "description": "Search policy documents.",
            "implementation_type": "rest",
            "endpoint_url": "https://policy.example.test/search",
            "method": "POST",
            "auth_type": "api_key",
            "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
            "output_schema": {"type": "object", "properties": {"results": {"type": "array"}}},
            "risk_class": "medium",
            "allowed_agents": [agent_id],
            "allowed_actions": ["read", "search"],
            "timeout_seconds": 30,
        },
    )
    rule_response = client.post(
        "/studio/rules",
        headers=headers,
        json={
            "name": "restricted-data-review",
            "condition": "Require approval before restricted data leaves the tenant.",
            "decision": "human_review",
        },
    )
    workflow_response = client.post(
        "/studio/workflows",
        headers=headers,
        json={
            "agent_id": agent_id,
            "name": "Policy Review Workflow",
            "nodes": [
                {"node_type": "trigger", "name": "Request received", "position": 0},
                {
                    "node_type": "tool",
                    "name": "Search policy",
                    "service_ref": "policy.search",
                    "instruction": "Find matching policy documents.",
                    "position": 1,
                },
            ],
        },
    )

    prompts = client.get("/studio/prompts", headers=headers).json()["prompts"]
    tools = client.get("/studio/tools", headers=headers).json()["tools"]
    rules = client.get("/studio/rules", headers=headers).json()["rules"]
    workflows = client.get(
        f"/studio/workflows?agent_id={agent_id}", headers=headers
    ).json()["workflows"]

    assert prompt_response.status_code == 201
    assert tool_response.status_code == 201
    assert rule_response.status_code == 201
    assert workflow_response.status_code == 201
    assert prompts[0]["template"]["name"] == "policy-review-system"
    assert tools[0]["name"] == "policy.search"
    assert rules[0]["name"] == "restricted-data-review"
    assert workflows[0]["agent_id"] == agent_id
    assert workflows[0]["nodes"][1]["service_ref"] == "policy.search"
    assert tools[0]["implementation_type"] == "rest"
    assert tools[0]["endpoint_url"] == "https://policy.example.test/search"
    assert tools[0]["auth_type"] == "api_key"


def test_tool_studio_test_runner_uses_gateway_permissions() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}
    agent_response = client.post(
        "/agents",
        headers=headers,
        json={"name": "Tool Runner Agent", "owner": "platform-team"},
    )
    agent_id = agent_response.json()["agent"]["agent_id"]
    client.post(
        "/studio/tools",
        headers=headers,
        json={
            "name": "customer.lookup",
            "description": "Lookup customer record.",
            "implementation_type": "echo",
            "risk_class": "medium",
            "allowed_agents": [agent_id],
            "allowed_actions": ["read"],
            "timeout_seconds": 15,
        },
    )

    allowed_response = client.post(
        "/studio/tools/customer.lookup/test",
        headers=headers,
        json={"agent_id": agent_id, "action": "read", "payload": {"customer_id": "123"}},
    )
    denied_response = client.post(
        "/studio/tools/customer.lookup/test",
        headers=headers,
        json={"agent_id": agent_id, "action": "delete", "payload": {"customer_id": "123"}},
    )

    assert allowed_response.status_code == 200
    assert allowed_response.json()["result"]["output"]["echo"]["customer_id"] == "123"
    assert denied_response.status_code == 403
    assert "action is not allowed" in denied_response.json()["detail"]
