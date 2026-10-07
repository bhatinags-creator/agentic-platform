from datetime import UTC, datetime, timedelta

from platform_common.domain.models import RetentionPolicy
from services.memory_governance.service import MemoryGovernanceService, MemoryType


def test_memory_retention_defaults_are_typed() -> None:
    service = MemoryGovernanceService()

    assert service.retention_for(MemoryType.SESSION) == "24h"
    assert service.retention_for("conversation") == "90d"
    assert service.retention_for("human_decisions") == "7y"


def test_memory_record_has_retention_and_expiry() -> None:
    service = MemoryGovernanceService()

    record = service.create_record(
        tenant_id="tenant-a",
        agent_id="agent.support",
        run_id="run-1",
        trace_id="trace-1",
        memory_type=MemoryType.CONVERSATION,
        content={"message": "hello"},
    )

    assert record.retention == RetentionPolicy.DAYS_90
    assert record.expires_at is not None
    assert record.expires_at > record.created_at
    assert service.list_records(tenant_id="tenant-a", run_id="run-1") == [record]


def test_runtime_only_memory_can_be_purged() -> None:
    service = MemoryGovernanceService()
    record = service.create_record(
        tenant_id="tenant-a",
        agent_id="agent.support",
        run_id="run-1",
        trace_id="trace-1",
        memory_type=MemoryType.AGENT_WORKING_MEMORY,
        content={"scratchpad": "temporary"},
    )

    purged = service.purge_expired(now=datetime.now(UTC) + timedelta(seconds=1))

    assert purged == [record]
    assert service.list_records(tenant_id="tenant-a") == []


def test_policy_controlled_memory_has_no_automatic_expiry() -> None:
    service = MemoryGovernanceService()

    record = service.create_record(
        tenant_id="tenant-a",
        agent_id="agent.support",
        run_id="run-1",
        trace_id="trace-1",
        memory_type=MemoryType.SEMANTIC_MEMORY,
        content={"fact": "customer prefers email"},
        policy_ref="policy.memory.semantic-default",
    )

    assert record.retention == RetentionPolicy.POLICY_CONTROLLED
    assert record.expires_at is None
    assert record.policy_ref == "policy.memory.semantic-default"
