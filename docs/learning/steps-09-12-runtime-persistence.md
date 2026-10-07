# Steps 09-12 - Persistent Runtime, Audit, FinOps, and Memory Stores

## What We Built

We added durable SQLite-backed repositories for the Runtime Plane governance stack.

Steps covered:

- Step 09 - Persistent Runtime Run Store
- Step 10 - Persistent Audit Store
- Step 11 - Persistent FinOps Store
- Step 12 - Persistent Memory Store

## Files Changed

- `services/runtime_execution/sqlite_repository.py`
- `services/audit_service/service.py`
- `services/finops_service/service.py`
- `services/memory_governance/service.py`
- `apps/runtime_api/main.py`
- `tests/test_runtime_persistence.py`
- `.env.example`

## Step 09 - Persistent Runtime Run Store

### `SQLiteAgentRunRepository`

Stores `AgentRun` records in SQLite.

Methods:

- `__init__(database_path)`: creates DB folder and schema.
- `save_run(run)`: inserts or updates a run.
- `get_run(tenant_id, run_id)`: loads a tenant-scoped run.
- `list_runs(tenant_id)`: lists runs for a tenant.
- `_initialize_schema()`: creates `agent_runs` table and indexes.
- `_connect()`: opens a SQLite connection.

Why it matters:

Runtime history now survives API restarts.

## Step 10 - Persistent Audit Store

### `AuditRepository`

Storage contract for audit events.

### `InMemoryAuditRepository`

Development in-memory implementation.

### `SQLiteAuditRepository`

Durable SQLite implementation.

Methods:

- `save_event(event)`: stores an `EventEnvelope`.
- `list_events(tenant_id=None, trace_id=None)`: queries audit events.
- `_initialize_schema()`: creates `audit_events` table and indexes.

### `AuditService`

Now depends on a repository.

Methods:

- `write(event)`: delegates to repository.
- `list_events(...)`: delegates to repository.
- `records`: compatibility property returning all events.

Why it matters:

Audit is enterprise evidence. It must not disappear on restart.

## Step 11 - Persistent FinOps Store

### `FinOpsRepository`

Storage contract for cost events.

### `InMemoryFinOpsRepository`

Development in-memory implementation.

### `SQLiteFinOpsRepository`

Durable SQLite implementation.

Methods:

- `save_event(event)`: stores one `CostEvent`.
- `list_events(...)`: filters by tenant, agent, run, and department.
- `_initialize_schema()`: creates `cost_events` table and indexes.

### `AIFinOpsService`

Now depends on a repository.

Existing methods continue to work:

- `record_model_usage(...)`
- `list_events(...)`
- `summarize_tenant(...)`
- `total_cost_by_tenant(...)`
- `total_cost_by_agent(...)`
- `total_cost_by_department(...)`

Why it matters:

Cost history survives restart and can support dashboards, budgets, showback, and chargeback.

## Step 12 - Persistent Memory Store

### `MemoryRepository`

Storage contract for governed memory records.

### `InMemoryMemoryRepository`

Development in-memory implementation.

### `SQLiteMemoryRepository`

Durable SQLite implementation.

Methods:

- `save_record(record)`: stores one memory record.
- `list_records(...)`: filters by tenant, agent, run, and memory type.
- `delete_records(memory_ids)`: deletes selected memory records.
- `_initialize_schema()`: creates `memory_records` table and indexes.

### `MemoryGovernanceService`

Now depends on a repository.

Existing methods continue to work:

- `create_record(...)`
- `list_records(...)`
- `purge_expired(...)`
- `retention_for(...)`

Why it matters:

Governed memory records can survive restart and still be purged according to retention policy.

## Runtime API Default Wiring

`apps/runtime_api/main.py` now builds a persistent local runtime by default.

Default DB path:

```text
E:\AIProjects\agentic-platform\data\agentic_platform_runtime.db
```

Environment override:

```text
AGENTIC_PLATFORM_RUNTIME_DB_PATH=E:\AIProjects\agentic-platform\data\agentic_platform_runtime.db
```

The same SQLite database contains:

- `agent_runs`
- `audit_events`
- `cost_events`
- `memory_records`

## Tests Added

`tests/test_runtime_persistence.py` verifies:

- runs survive new service instances
- audit events survive new service instances
- cost events survive new service instances
- memory records survive and can be purged

## Learning Point

Once a platform has runtime, audit, cost, and memory signals, persistence becomes a core reliability feature.

A process restart should not erase operational history, evidence, spend, or governed memory.
