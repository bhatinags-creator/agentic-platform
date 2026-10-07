import pytest

from services.audit_service.service import AuditService, SQLiteAuditRepository
from services.finops_service.service import AIFinOpsService, SQLiteFinOpsRepository
from services.memory_governance.service import (
    MemoryGovernanceService,
    MemoryType,
    SQLiteMemoryRepository,
)
from services.runtime_execution.service import RuntimeExecutionService
from services.runtime_execution.sqlite_repository import SQLiteAgentRunRepository


@pytest.mark.anyio
async def test_sqlite_runtime_repository_persists_runs_across_service_instances(tmp_path) -> None:
    database_path = tmp_path / "runtime.db"
    first_service = RuntimeExecutionService(repository=SQLiteAgentRunRepository(database_path))
    run = await first_service.start_run(
        tenant_id="tenant-a",
        user_id="user-1",
        agent_id="agent.support",
        agent_version="1.0.0",
        input_payload={"message": "hello"},
    )

    second_service = RuntimeExecutionService(repository=SQLiteAgentRunRepository(database_path))
    loaded_run = second_service.get_run("tenant-a", run.run_id)

    assert loaded_run.run_id == run.run_id
    assert loaded_run.status == "completed"
    assert len(second_service.list_runs("tenant-a")) == 1


@pytest.mark.anyio
async def test_sqlite_audit_repository_persists_events_across_service_instances(tmp_path) -> None:
    database_path = tmp_path / "runtime.db"
    first_audit = AuditService(repository=SQLiteAuditRepository(database_path))
    first_service = RuntimeExecutionService(audit_service=first_audit)
    run = await first_service.start_run(
        tenant_id="tenant-a",
        user_id="user-1",
        agent_id="agent.support",
        agent_version="1.0.0",
        input_payload={"message": "hello"},
    )

    second_audit = AuditService(repository=SQLiteAuditRepository(database_path))
    events = second_audit.list_events(tenant_id="tenant-a", trace_id=run.trace_id)

    assert [event.event_type for event in events] == [
        "agent_run.started",
        "agent_run.policy_evaluated",
        "agent_run.cost_recorded",
        "agent_run.responsible_ai_checked",
        "agent_run.memory_recorded",
        "agent_run.completed",
    ]


def test_sqlite_finops_repository_persists_cost_events_across_service_instances(tmp_path) -> None:
    database_path = tmp_path / "runtime.db"
    first_finops = AIFinOpsService(repository=SQLiteFinOpsRepository(database_path))
    first_finops.record_model_usage(
        tenant_id="tenant-a",
        agent_id="agent.support",
        run_id="run-1",
        trace_id="trace-1",
        provider="mock",
        model="mock-model",
        prompt_tokens=10,
        completion_tokens=5,
        estimated_cost=0.25,
        department="support",
    )

    second_finops = AIFinOpsService(repository=SQLiteFinOpsRepository(database_path))
    summary = second_finops.summarize_tenant("tenant-a")

    assert summary.total_runs == 1
    assert summary.total_tokens == 15
    assert summary.total_cost == 0.25
    assert second_finops.total_cost_by_department("tenant-a", "support") == 0.25


def test_sqlite_memory_repository_persists_and_purges_records(tmp_path) -> None:
    database_path = tmp_path / "runtime.db"
    first_memory = MemoryGovernanceService(repository=SQLiteMemoryRepository(database_path))
    record = first_memory.create_record(
        tenant_id="tenant-a",
        agent_id="agent.support",
        run_id="run-1",
        trace_id="trace-1",
        memory_type=MemoryType.AGENT_WORKING_MEMORY,
        content={"scratchpad": "temporary"},
    )

    second_memory = MemoryGovernanceService(repository=SQLiteMemoryRepository(database_path))
    loaded_records = second_memory.list_records(tenant_id="tenant-a", run_id="run-1")
    purged_records = second_memory.purge_expired()

    assert loaded_records[0].memory_id == record.memory_id
    assert purged_records[0].memory_id == record.memory_id
    assert second_memory.list_records(tenant_id="tenant-a") == []



