# Step 06 - Runtime Policy Gate and Audit Trail

## What We Built

We added enterprise control and traceability to the Runtime Plane.

Files changed:

- `services/policy_engine/service.py`
- `services/audit_service/service.py`
- `services/runtime_execution/service.py`
- `apps/runtime_api/main.py`
- `tests/test_runtime_execution.py`
- `tests/test_runtime_api.py`

## Component Purpose

A production agent runtime should not execute every request blindly.

Before model, tool, and RAG calls happen, the platform needs a policy decision. Around the run, the platform needs audit events that prove what happened.

This step adds both patterns.

## Policy Engine

File: `services/policy_engine/service.py`

### `PolicyEngineService`

Evaluates whether a platform action should be permitted.

### `evaluate(action, subject, resource)`

Inputs:

- `action`: operation being attempted, such as `agent_run.start`.
- `subject`: who is attempting the action.
- `resource`: what the action targets.

Behavior:

- If input contains `policy_decision: deny`, returns a deny decision.
- Otherwise returns a permit decision.

Returns:

- `PolicyDecision`

Why this simple rule exists: it gives us a testable policy gate now. Later, this method can call OPA, Cedar, custom ABAC/RBAC rules, risk policies, model restrictions, or tenant-specific governance rules.

## Audit Service

File: `services/audit_service/service.py`

### `AuditService`

In-memory audit recorder for development and tests.

### `__init__()`

Creates `records`, a list of `EventEnvelope` objects.

### `write(event)`

Appends an event to the audit records.

Returns:

- the same `EventEnvelope`

### `list_events(tenant_id=None, trace_id=None)`

Returns audit events.

Filters:

- by tenant if `tenant_id` is provided
- by trace if `trace_id` is provided

## Runtime Execution Updates

File: `services/runtime_execution/service.py`

### `RuntimePolicyDeniedError`

Raised when policy denies a run.

Fields stored on the exception:

- `run`: the failed `AgentRun`
- `decision`: the `PolicyDecision`

This lets the API return a useful 403 response with run and decision identifiers.

### `RuntimeExecutionService.__init__(...)`

New dependencies added:

- `policy_engine`
- `audit_service`

If not provided, default services are created.

### `start_run(...)`

The execution flow now is:

1. Create a running `AgentRun`.
2. Write `agent_run.started` audit event.
3. Evaluate policy for `agent_run.start`.
4. Write `agent_run.policy_evaluated` audit event.
5. If denied, save failed run, write `agent_run.denied`, raise `RuntimePolicyDeniedError`.
6. If permitted, call RAG, Tool Gateway, and Model Gateway.
7. Save completed run.
8. Write `agent_run.completed` audit event.

Output now includes a `policy` section for permitted runs.

### `list_audit_events(tenant_id=None, trace_id=None)`

Returns audit events from the audit service.

Useful for tests and later admin/debug endpoints.

### `_write_audit_event(event_type, run, payload)`

Creates an `EventEnvelope` and writes it to audit.

Important fields:

- `event_type`
- `tenant_id`
- `trace_id`
- `correlation_id`: run id
- `actor`: user who started the run
- `subject`: agent run
- `payload`: agent id, version, status, and event-specific fields
- `idempotency_key`: run id plus event type

## Runtime API Update

File: `apps/runtime_api/main.py`

### `start_run(...)`

Now catches `RuntimePolicyDeniedError`.

If policy denies execution, the API returns:

```text
403 Forbidden
```

Response detail includes:

- `code`
- `message`
- `run_id`
- `policy_decision_id`
- `reason`

## Tests Added

Runtime service tests now verify:

- permitted runs include policy output
- completed runs emit audit events
- denied runs are saved as failed
- denied runs emit started, policy evaluated, and denied audit events

Runtime API tests now verify:

- denied requests return 403
- 403 response includes run and policy decision identifiers

## Learning Point

Policy and audit are cross-cutting platform capabilities.

They should not be hidden inside model calls or tool calls. The runtime orchestration layer should call them deliberately so every execution has control and evidence.
