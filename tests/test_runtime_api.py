from fastapi.testclient import TestClient

from apps.runtime_api.main import create_app
from services.finops_service.service import AIFinOpsService
from services.policy_engine.service import PolicyEngineService
from services.runtime_execution.service import RuntimeExecutionService


def build_client(runtime: RuntimeExecutionService | None = None) -> TestClient:
    return TestClient(create_app(runtime=runtime or RuntimeExecutionService()))


def test_runtime_health_endpoint() -> None:
    client = build_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "runtime-api"}


def test_start_get_and_list_agent_run() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}

    start_response = client.post(
        "/agent-runs",
        headers=headers,
        json={
            "user_id": "user-1",
            "agent_id": "agent.customer-support",
            "agent_version": "1.0.0",
            "input": {"message": "hello"},
        },
    )

    assert start_response.status_code == 201
    run = start_response.json()["run"]
    assert run["status"] == "completed"
    assert run["tenant_id"] == "tenant-a"
    assert run["output"]["policy"]["decision"] == "permit"
    assert run["output"]["model"]["output_text"] == "MVP model gateway response"

    get_response = client.get(f"/agent-runs/{run['run_id']}", headers=headers)
    list_response = client.get("/agent-runs", headers=headers)

    assert get_response.status_code == 200
    assert get_response.json()["run"]["run_id"] == run["run_id"]
    assert len(list_response.json()["runs"]) == 1


def test_start_agent_run_returns_forbidden_when_policy_denies() -> None:
    client = build_client(
        RuntimeExecutionService(
            policy_engine=PolicyEngineService(allow_client_decision_override=True)
        )
    )

    response = client.post(
        "/agent-runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={
            "user_id": "user-1",
            "agent_id": "agent.customer-support",
            "agent_version": "1.0.0",
            "input": {"policy_decision": "deny"},
        },
    )

    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["code"] == "policy_denied"
    assert detail["run_id"]
    assert detail["policy_decision_id"]


def test_agent_run_is_tenant_scoped() -> None:
    client = build_client()
    start_response = client.post(
        "/agent-runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={
            "user_id": "user-1",
            "agent_id": "agent.customer-support",
            "agent_version": "1.0.0",
            "input": {"message": "hello"},
        },
    )
    run_id = start_response.json()["run"]["run_id"]

    response = client.get(f"/agent-runs/{run_id}", headers={"X-Tenant-ID": "tenant-b"})

    assert response.status_code == 404



def test_start_agent_run_returns_too_many_requests_when_budget_is_exceeded() -> None:
    finops_service = AIFinOpsService()
    finops_service.set_tenant_budget("tenant-a", 0)
    client = build_client(RuntimeExecutionService(finops_service=finops_service))

    response = client.post(
        "/agent-runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={
            "user_id": "user-1",
            "agent_id": "agent.customer-support",
            "agent_version": "1.0.0",
            "input": {"message": "hello"},
        },
    )

    assert response.status_code == 429
    detail = response.json()["detail"]
    assert detail["code"] == "budget_exceeded"
    assert detail["run_id"]


def test_start_agent_run_rejects_unknown_request_fields() -> None:
    client = build_client()

    response = client.post(
        "/agent-runs",
        headers={"X-Tenant-ID": "tenant-a"},
        json={
            "user_id": "user-1",
            "agent_id": "agent.customer-support",
            "agent_version": "1.0.0",
            "input": {"message": "hello"},
            "typo": "should fail",
        },
    )

    assert response.status_code == 422



def test_runtime_metrics_endpoint_returns_tenant_snapshot() -> None:
    client = build_client()
    headers = {"X-Tenant-ID": "tenant-a"}
    client.post(
        "/agent-runs",
        headers=headers,
        json={
            "user_id": "user-1",
            "agent_id": "agent.customer-support",
            "agent_version": "1.0.0",
            "input": {"message": "hello"},
        },
    )

    response = client.get("/metrics", headers=headers)

    assert response.status_code == 200
    metrics = response.json()
    assert metrics["tenant_id"] == "tenant-a"
    assert metrics["total_runs"] == 1
    assert metrics["completed_runs"] == 1
    assert metrics["total_tokens"] > 0
    assert metrics["completed_traces"] == 1


def test_optional_api_key_auth_protects_runtime_api(monkeypatch) -> None:
    monkeypatch.setenv("AGENTIC_PLATFORM_API_KEY", "secret")
    client = TestClient(create_app(runtime=RuntimeExecutionService()))

    missing_key_response = client.get("/metrics", headers={"X-Tenant-ID": "tenant-a"})
    valid_key_response = client.get(
        "/metrics",
        headers={"X-Tenant-ID": "tenant-a", "X-API-Key": "secret"},
    )

    assert missing_key_response.status_code == 401
    assert valid_key_response.status_code == 200
