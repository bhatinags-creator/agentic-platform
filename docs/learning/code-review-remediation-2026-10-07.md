# Code Review Remediation - 2026-10-07

Source: external Claude code review pasted by user.

This note separates fixes applied immediately from items that are valid but belong to later platform milestones.

## Fixed Now

### Packaging and Docker Build

Problem:

`pip install -e .` failed because setuptools discovered multiple top-level packages in a flat-layout project.

Fix:

- Added `[build-system]` to `pyproject.toml`.
- Added `[tool.setuptools.packages.find]` with explicit package includes.
- Verified `python -m pip install -e .` succeeds.
- Added `.dockerignore`.
- Updated `Dockerfile` to run as a non-root user.

### Failed Runtime Runs

Problem:

If gateway, model, or FinOps work raised after a run was saved as `RUNNING`, the run could stay `RUNNING` forever.

Fix:

- Added `RuntimeExecutionFailedError`.
- Wrapped post-policy execution in failure handling.
- Failed runs are saved with `AgentRunStatus.FAILED`.
- Runtime now writes `agent_run.failed` audit events.
- Budget failures map to HTTP `429`.

### FinOps Budget Enforcement

Problem:

The mock model emitted token counts but zero estimated cost, which meant budgets could not be meaningfully enforced.

Fix:

- `ModelGatewayService` now emits deterministic mock cost based on total tokens.
- Added regression tests for exceeded budget handling.

### Append-Only Audit Persistence

Problem:

`SQLiteAuditRepository.save_event` used an upsert, allowing an existing audit event to be overwritten.

Fix:

- Changed audit persistence to plain `INSERT`.
- Added a regression test proving duplicate audit event IDs raise `sqlite3.IntegrityError`.

### SQLite Connection Cleanup

Problem:

`with sqlite3.connect(...) as conn` commits or rolls back but does not close the connection.

Fix:

- Wrapped SQLite connections with `contextlib.closing(...)` across current SQLite repositories.

### Tenant-Scoped Service APIs

Problem:

Some service-level list methods allowed `tenant_id=None`, which could return cross-tenant data.

Fix:

- `AuditService.list_events(...)` now requires `tenant_id`.
- `AIFinOpsService.list_events(...)` now requires `tenant_id`.
- `MemoryGovernanceService.list_records(...)` now requires `tenant_id`.
- Low-level repository methods remain flexible for internal maintenance jobs such as memory purge.

### Policy Test Hook

Problem:

The MVP policy engine denied runs based on client-controlled input: `input.policy_decision == "deny"`.

Fix:

- Added `PolicyEngineService(allow_client_decision_override=False)` default.
- Client-controlled policy denial is now disabled unless explicitly enabled in tests.

### Request Schema Strictness

Problem:

Runtime request schemas accepted extra fields silently.

Fix:

- Added `ConfigDict(extra="forbid")` to `StartRunRequest`.
- Added API test for unknown field rejection.

### Container-Unsafe Local Paths

Problem:

`.env.example` contained Windows `E:\...` paths that are invalid inside Linux containers.

Fix:

- Changed local DB paths to relative `data/...` paths.

### Docs as Python Packages

Problem:

`docs/` had `__init__.py` markers even though docs do not need to be installed as Python packages.

Fix:

- Removed `docs/__init__.py` and nested docs package markers.

## Deferred Architecture Items

These review points are valid but should be handled in planned roadmap steps rather than rushed into the MVP patch:

- JWT/authentication and deriving tenant/user from verified identity.
- Runtime validation that `agent_id` and `agent_version` resolve to a published registry version.
- Enforcing manifest execution, tool, memory, human approval, and observability policies at runtime.
- Durable Agent Studio draft persistence.
- Pagination on list endpoints.
- Client-supplied idempotency keys for `POST /agent-runs`.
- Async worker execution instead of doing all runtime work inside the HTTP request.
- Durable tenant budget storage and concurrency-safe budget reservation.
- Automated memory retention purge worker.
- Full audit redaction/hash-only prompt capture according to observability policy.
- Dependency pinning or lockfile strategy.
- Kubernetes probes, resource limits, and production deployment hardening.

## Verification

```text
python -m pip install -e .
Successfully installed agentic-platform-0.1.0

python -m ruff check .
All checks passed!

python -m pytest
62 passed, 1 warning
```
