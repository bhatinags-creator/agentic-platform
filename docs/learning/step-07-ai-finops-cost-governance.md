# Step 07 - AI FinOps Cost Governance

## What We Built

We made AI cost tracking a first-class platform capability.

Files changed:

- `services/finops_service/service.py`
- `services/runtime_execution/service.py`
- `tests/test_finops_service.py`
- `tests/test_runtime_execution.py`

## Component Purpose

AI platforms need to track cost and token usage by tenant, agent, run, workflow, and department.

Without this, enterprise teams cannot answer:

- Which tenant is spending the most?
- Which agent is expensive?
- Which department should receive showback or chargeback?
- Are token trends growing?
- Should a budget stop execution?

## `CostEvent`

File: `services/finops_service/service.py`

Immutable dataclass representing one model usage cost event.

Fields:

- `event_id`: unique event identifier.
- `tenant_id`: tenant that owns the cost.
- `agent_id`: agent responsible for the cost.
- `run_id`: runtime run that generated the cost.
- `trace_id`: trace for cross-service observability.
- `workflow_id`: optional workflow/business process identifier.
- `department`: optional department for showback/chargeback.
- `provider`: model provider.
- `model`: model name.
- `prompt_tokens`: input token count.
- `completion_tokens`: output token count.
- `total_tokens`: combined token count.
- `estimated_cost`: estimated monetary cost.
- `occurred_at`: timestamp.

## `CostSummary`

Aggregated tenant cost view.

Fields:

- `tenant_id`
- `total_runs`
- `total_prompt_tokens`
- `total_completion_tokens`
- `total_tokens`
- `total_cost`

## `BudgetExceededError`

Raised when recording a cost event would exceed a tenant budget.

This is the first budget enforcement hook. Later we can move budget checks before expensive model calls.

## `AIFinOpsService`

Tracks AI usage and cost events.

### `__init__()`

Creates:

- `events`: in-memory list of `CostEvent`
- `tenant_budgets`: tenant budget limits

### `set_tenant_budget(tenant_id, budget)`

Sets a tenant budget.

Rules:

- budget must be zero or positive
- negative budget raises `ValueError`

### `record_model_usage(...)`

Records one model cost event.

Inputs include:

- tenant, agent, run, trace
- provider/model
- prompt/completion tokens
- estimated cost
- optional workflow and department

Behavior:

1. Calculate projected tenant cost.
2. Check configured tenant budget.
3. Raise `BudgetExceededError` if budget would be exceeded.
4. Create `CostEvent`.
5. Append it to `events`.
6. Return the event.

### `list_events(tenant_id=None, agent_id=None, run_id=None, department=None)`

Filters cost events by dimensions.

This supports cost exploration and later dashboards.

### `summarize_tenant(tenant_id)`

Aggregates usage for one tenant.

Returns:

- `CostSummary`

### `total_cost_by_tenant(tenant_id)`

Returns total tenant spend.

### `total_cost_by_agent(tenant_id, agent_id)`

Returns spend for one agent inside one tenant.

### `total_cost_by_department(tenant_id, department)`

Returns spend for one department inside one tenant.

## Runtime Integration

File: `services/runtime_execution/service.py`

`RuntimeExecutionService` now accepts:

- `finops_service`

After the model call, runtime records model usage with:

- tenant
- agent
- run
- trace
- provider/model
- prompt/completion tokens
- estimated cost
- optional `workflow_id` from input payload
- optional `department` from input payload

Runtime output now includes:

```text
output.finops
```

with:

- cost event id
- prompt tokens
- completion tokens
- total tokens
- estimated cost
- department
- workflow id

Runtime also writes audit event:

```text
agent_run.cost_recorded
```

## Tests Added

`tests/test_finops_service.py` verifies:

- model usage is recorded
- tenant summaries are calculated
- cost by agent works
- cost by department works
- tenant budgets can block cost recording

`tests/test_runtime_execution.py` verifies:

- runtime output includes FinOps details
- runtime records a FinOps cost event
- runtime emits `agent_run.cost_recorded` audit event

## Learning Point

FinOps is not just a report. It is a platform service.

The runtime must emit cost signals at the point where usage happens. Dashboards, budgets, chargeback, and governance all depend on those events.
