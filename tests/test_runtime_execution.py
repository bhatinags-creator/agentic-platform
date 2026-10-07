import pytest

from platform_common.domain.models import AgentRunStatus
from services.finops_service.service import AIFinOpsService
from services.runtime_execution.service import RuntimeExecutionService, RuntimePolicyDeniedError


@pytest.mark.anyio
async def test_runtime_execution_completes_run_and_records_outputs() -> None:
    service = RuntimeExecutionService()

    run = await service.start_run(
        tenant_id="tenant-a",
        user_id="user-1",
        agent_id="agent.customer-support",
        agent_version="1.0.0",
        input_payload={"message": "hello", "department": "support"},
    )

    assert run.status == AgentRunStatus.COMPLETED
    assert run.output is not None
    assert run.output["policy"]["decision"] == "permit"
    assert run.output["finops"]["total_tokens"] > 0
    assert run.output["finops"]["department"] == "support"
    assert run.output["memory"]["memory_type"] == "conversation"
    assert run.output["memory"]["retention"] == "90d"
    assert run.output["responsible_ai"]["status"] == "passed"
    assert run.output["model"]["output_text"] == "MVP model gateway response"
    assert run.output["tool"]["status"] == "succeeded"
    assert run.output["retrievals"][0]["document_id"] == "doc-mvp-001"


@pytest.mark.anyio
async def test_runtime_execution_records_finops_usage() -> None:
    finops_service = AIFinOpsService()
    service = RuntimeExecutionService(finops_service=finops_service)

    run = await service.start_run(
        tenant_id="tenant-a",
        user_id="user-1",
        agent_id="agent.customer-support",
        agent_version="1.0.0",
        input_payload={"message": "hello", "workflow_id": "wf-1", "department": "support"},
    )
    events = finops_service.list_events(tenant_id="tenant-a", run_id=str(run.run_id))

    assert len(events) == 1
    assert events[0].agent_id == "agent.customer-support"
    assert events[0].workflow_id == "wf-1"
    assert events[0].department == "support"
    assert events[0].total_tokens > 0


@pytest.mark.anyio
async def test_runtime_execution_records_memory_governance() -> None:
    service = RuntimeExecutionService()

    run = await service.start_run(
        tenant_id="tenant-a",
        user_id="user-1",
        agent_id="agent.customer-support",
        agent_version="1.0.0",
        input_payload={"message": "remember this interaction"},
    )
    records = service.list_memory_records(tenant_id="tenant-a", run_id=str(run.run_id))

    assert len(records) == 1
    assert records[0].memory_type == "conversation"
    assert records[0].retention == "90d"
    assert records[0].content["model_output"] == "MVP model gateway response"


@pytest.mark.anyio
async def test_runtime_execution_writes_audit_events_for_completed_run() -> None:
    service = RuntimeExecutionService()

    run = await service.start_run(
        tenant_id="tenant-a",
        user_id="user-1",
        agent_id="agent.customer-support",
        agent_version="1.0.0",
        input_payload={"message": "hello"},
    )
    events = service.list_audit_events(tenant_id="tenant-a", trace_id=run.trace_id)

    assert [event.event_type for event in events] == [
        "agent_run.started",
        "agent_run.policy_evaluated",
        "agent_run.cost_recorded",
        "agent_run.responsible_ai_checked",
        "agent_run.memory_recorded",
        "agent_run.completed",
    ]
    assert events[0].correlation_id == str(run.run_id)


@pytest.mark.anyio
async def test_runtime_execution_denies_run_when_policy_denies() -> None:
    service = RuntimeExecutionService()

    with pytest.raises(RuntimePolicyDeniedError) as exc_info:
        await service.start_run(
            tenant_id="tenant-a",
            user_id="user-1",
            agent_id="agent.customer-support",
            agent_version="1.0.0",
            input_payload={"policy_decision": "deny"},
        )

    denied_run = exc_info.value.run
    assert denied_run.status == AgentRunStatus.FAILED
    assert denied_run.output is not None
    assert denied_run.output["error"] == "policy_denied"

    events = service.list_audit_events(tenant_id="tenant-a", trace_id=denied_run.trace_id)
    assert [event.event_type for event in events] == [
        "agent_run.started",
        "agent_run.policy_evaluated",
        "agent_run.denied",
    ]


def test_runtime_execution_lists_runs_by_tenant(anyio_backend_name) -> None:
    assert anyio_backend_name in {"asyncio", "trio"}




