# Steps 36-40 - Observability, Metrics, SDK, CLI, and Local Agent Studio UI

Date completed: 2026-10-08

## Purpose

These steps add operational visibility and developer experience. The platform now records traces and spans, exposes tenant metrics, expands the Python SDK, provides a CLI entry point, and serves a minimal local Agent Studio UI.

## Step 36 - Trace and Span Model

File:

- `observability/service.py`

Implemented:

- trace records
- span records
- trace status lifecycle
- span status lifecycle
- tenant-scoped trace listing
- span listing by trace
- trace count aggregation

Runtime integration:

- `RuntimeExecutionService` starts a trace for each run.
- Runtime records spans for policy evaluation, RAG retrieval, tool invocation, and model invocation.
- Runtime finishes traces as completed, failed, or waiting.

## Step 37 - Metrics API

Files:

- `services/runtime_execution/service.py`
- `apps/runtime_api/main.py`

Implemented metrics:

- total runs
- completed runs
- failed runs
- waiting runs
- policy denials
- total cost
- total tokens
- memory records
- open traces
- completed traces

Endpoint:

```text
GET /metrics
```

Requires:

```text
X-Tenant-ID
```

## Step 38 - Python SDK Expansion

File:

- `sdk/python/agentic_platform_client/client.py`

Implemented SDK methods:

- `create_agent(...)`
- `list_agents()`
- `get_agent(...)`
- `publish_agent_version(...)`
- `list_agent_versions(...)`
- `create_agent_draft(...)`
- `list_agent_drafts()`
- `start_run(...)`
- `list_runs()`
- `get_run(...)`
- `get_metrics()`

The SDK now carries `X-Tenant-ID` automatically.

## Step 39 - CLI Tool

Files:

- `sdk/python/agentic_platform_client/cli.py`
- `pyproject.toml`

Console command:

```text
agentic-platform
```

Implemented commands:

- `create-agent`
- `list-agents`
- `start-run`
- `get-run`
- `list-runs`
- `metrics`
- `list-drafts`

Example:

```powershell
agentic-platform --tenant-id tenant-a metrics
```

## Step 40 - Minimal Local Agent Studio UI

File:

- `apps/control_plane_api/main.py`

Endpoint:

```text
GET /studio
```

Implemented:

- tenant input
- refresh action
- agents table
- drafts table
- browser-side calls to existing Control Plane APIs

Learning point:

This is not the final Agent Studio product UI. It is the first usable local workbench surface, built on the APIs already developed.

## Tests

Added or updated:

- `tests/test_observability_service.py`
- `tests/test_runtime_api.py`
- `tests/test_cli.py`
- `tests/test_control_plane_api.py`

## Verification

```text
python -m ruff check .
All checks passed!

python -m pytest
87 passed, 1 warning
```

## Learning Summary

This batch makes the platform easier to operate and easier to use:

```text
Trace execution -> Measure tenant metrics -> Use SDK -> Use CLI -> Open local Studio UI
```
