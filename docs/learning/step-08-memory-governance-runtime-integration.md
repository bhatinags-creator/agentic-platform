# Step 08 - Memory Governance Runtime Integration

## What We Built

We made memory governance a runtime platform capability.

Files changed:

- `services/memory_governance/service.py`
- `services/runtime_execution/service.py`
- `tests/test_memory_governance.py`
- `tests/test_runtime_execution.py`

## Component Purpose

Enterprise memory cannot be treated like a generic cache.

Different memory types need different retention rules:

- session memory: short lived
- conversation memory: medium retention
- agent working memory: runtime only
- semantic memory: policy controlled
- human decisions: long-term evidence

This step turns the earlier conceptual retention policy into executable behavior.

## `MemoryType`

File: `services/memory_governance/service.py`

Enum representing supported memory categories.

Values:

- `SESSION`
- `CONVERSATION`
- `AGENT_WORKING_MEMORY`
- `SEMANTIC_MEMORY`
- `HUMAN_DECISIONS`

## `MEMORY_RETENTION_DEFAULTS`

Maps each `MemoryType` to a `RetentionPolicy`.

Defaults:

- session -> 24 hours
- conversation -> 90 days
- agent working memory -> runtime only
- semantic memory -> policy controlled
- human decisions -> 7 years

## `MemoryRecord`

Immutable dataclass representing one governed memory record.

Fields:

- `memory_id`: unique memory record ID.
- `tenant_id`: tenant owner.
- `agent_id`: agent that produced the memory.
- `run_id`: runtime run that produced the memory.
- `trace_id`: trace for observability.
- `memory_type`: category of memory.
- `retention`: retention policy.
- `content`: stored memory content.
- `created_at`: creation timestamp.
- `expires_at`: calculated expiry timestamp, if automatic expiry applies.
- `policy_ref`: optional policy controlling memory retention.

## `MemoryGovernanceService`

Owns memory retention metadata and in-memory governed records.

### `__init__()`

Creates the in-memory record list.

### `retention_for(memory_type)`

Returns the retention policy value for a memory type.

Accepts:

- `MemoryType`
- string memory type

Returns:

- string retention value such as `24h`, `90d`, or `policy_controlled`

### `create_record(...)`

Creates a governed memory record.

Inputs:

- tenant
- agent
- run
- trace
- memory type
- content
- optional policy reference

Behavior:

1. Parse memory type.
2. Resolve default retention.
3. Calculate expiry timestamp.
4. Create `MemoryRecord`.
5. Store it.
6. Return it.

### `list_records(...)`

Filters memory records by:

- tenant
- agent
- run
- memory type

### `purge_expired(now=None)`

Removes expired records and returns the purged records.

Runtime-only records expire immediately and can be purged on the next cleanup pass.

### `_parse_memory_type(memory_type)`

Private helper that normalizes strings and enum values into `MemoryType`.

### `_expires_at(created_at, retention)`

Private helper that calculates expiry time.

Rules:

- runtime only -> created time
- 24 hours -> created time plus 24 hours
- 90 days -> created time plus 90 days
- 7 years -> created time plus 7 years
- policy controlled -> no automatic expiry

## Runtime Integration

File: `services/runtime_execution/service.py`

`RuntimeExecutionService` now accepts:

- `memory_governance`

After RAG, tool, model, and FinOps work, runtime creates a conversation memory record.

The memory record stores:

- input payload
- model output
- retrieval count
- tool status

Runtime output now includes:

```text
output.memory
```

with:

- memory id
- memory type
- retention
- expiry timestamp

Runtime also emits audit event:

```text
agent_run.memory_recorded
```

## Tests Added

`tests/test_memory_governance.py` verifies:

- retention defaults are typed
- records contain retention and expiry
- runtime-only memory can be purged
- policy-controlled memory has no automatic expiry

`tests/test_runtime_execution.py` verifies:

- runtime output includes memory governance details
- runtime stores one conversation memory record
- audit includes `agent_run.memory_recorded`

## Learning Point

Memory governance is more than storing chat history.

A governed platform must know what kind of memory it stores, who owns it, which run produced it, how long it may live, and whether policy controls its retention.
