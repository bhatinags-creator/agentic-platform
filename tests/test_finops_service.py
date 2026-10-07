import pytest

from services.finops_service.service import AIFinOpsService, BudgetExceededError


def test_finops_records_and_summarizes_model_usage() -> None:
    service = AIFinOpsService()

    service.record_model_usage(
        tenant_id="tenant-a",
        agent_id="agent.support",
        run_id="run-1",
        trace_id="trace-1",
        provider="mock",
        model="mock-model",
        prompt_tokens=10,
        completion_tokens=5,
        estimated_cost=0.25,
        workflow_id="workflow-claims",
        department="claims",
    )
    service.record_model_usage(
        tenant_id="tenant-a",
        agent_id="agent.support",
        run_id="run-2",
        trace_id="trace-2",
        provider="mock",
        model="mock-model",
        prompt_tokens=20,
        completion_tokens=10,
        estimated_cost=0.75,
        department="claims",
    )

    summary = service.summarize_tenant("tenant-a")

    assert summary.total_runs == 2
    assert summary.total_prompt_tokens == 30
    assert summary.total_completion_tokens == 15
    assert summary.total_tokens == 45
    assert summary.total_cost == 1.0
    assert service.total_cost_by_agent("tenant-a", "agent.support") == 1.0
    assert service.total_cost_by_department("tenant-a", "claims") == 1.0


def test_finops_enforces_tenant_budget() -> None:
    service = AIFinOpsService()
    service.set_tenant_budget("tenant-a", 0.5)

    with pytest.raises(BudgetExceededError):
        service.record_model_usage(
            tenant_id="tenant-a",
            agent_id="agent.support",
            run_id="run-1",
            trace_id="trace-1",
            provider="mock",
            model="mock-model",
            prompt_tokens=10,
            completion_tokens=5,
            estimated_cost=0.75,
        )
