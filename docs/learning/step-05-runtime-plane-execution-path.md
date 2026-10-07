# Step 05 - Runtime Plane Execution Path

## What We Built

We created the first Runtime Plane execution path.

Files:

- `services/runtime_execution/service.py`
- `apps/runtime_api/main.py`
- `apps/runtime_api/schemas.py`
- `tests/test_runtime_execution.py`
- `tests/test_runtime_api.py`

## Component Purpose

The Runtime Plane executes agent runs.

The Control Plane answers, "What agents exist and how are they governed?"

The Runtime Plane answers, "Run this agent version for this user input and record the result."

## Schema Classes in `apps/runtime_api/schemas.py`

### `StartRunRequest`

Request body for starting an agent run.

Fields:

- `user_id`: user requesting execution.
- `agent_id`: logical agent identity.
- `agent_version`: version to execute.
- `input`: runtime input payload.

Tenant is not included in the body. It comes from the `X-Tenant-ID` header.

### `AgentRunResponse`

Response wrapper for one `AgentRun`.

Field:

- `run`

### `AgentRunListResponse`

Response wrapper for multiple runs.

Field:

- `runs`

## Runtime Service Classes

File: `services/runtime_execution/service.py`

### `AgentRunNotFoundError`

Raised when a run cannot be found for the requested tenant.

The API maps this to HTTP 404.

### `AgentRunRepository`

Abstract storage contract for runtime execution history.

### `save_run(run)`

Persists an `AgentRun`.

Returns:

- saved `AgentRun`

### `get_run(tenant_id, run_id)`

Loads one tenant-scoped run.

Returns:

- `AgentRun` if found
- `None` if missing or tenant mismatch

### `list_runs(tenant_id)`

Lists all runs for one tenant.

## `InMemoryAgentRunRepository`

Development implementation of `AgentRunRepository`.

It stores runs in a dictionary.

### `__init__()`

Creates `_runs`, a dictionary keyed by run UUID.

### `save_run(run)`

Stores or replaces the run in `_runs`.

### `get_run(tenant_id, run_id)`

Looks up a run by ID and verifies tenant ownership.

### `list_runs(tenant_id)`

Returns tenant runs sorted by creation time.

## `RuntimeExecutionService`

Coordinates one MVP execution through platform gateways.

### `__init__(repository=None, model_gateway=None, tool_gateway=None, rag_platform=None)`

Accepts dependencies or creates defaults.

Dependencies:

- `repository`: stores run history.
- `model_gateway`: calls model provider abstraction.
- `tool_gateway`: invokes tools.
- `rag_platform`: retrieves context.

This is dependency injection. It makes the service easy to test and easy to replace later.

### `start_run(tenant_id, user_id, agent_id, agent_version, input_payload)`

Starts and completes one MVP run.

Steps:

1. Generate a `trace_id`.
2. Create an `AgentRun` with status `running`.
3. Save the running run.
4. Retrieve context from `RAGPlatformService`.
5. Invoke `ToolGatewayService` with `mvp.echo`.
6. Call `ModelGatewayService.chat(...)`.
7. Copy the run with status `completed`.
8. Store structured output with model, tool, and retrieval sections.
9. Save and return the completed run.

Returns:

- completed `AgentRun`

Current limitation:

- this is a simple synchronous orchestration path; future steps will add policy, audit, memory, cost tracking, and durable runtime storage.

### `get_run(tenant_id, run_id)`

Loads a tenant-scoped run.

Raises:

- `AgentRunNotFoundError` if missing.

### `list_runs(tenant_id)`

Returns all runs for a tenant.

### `_parse_uuid(value)`

Private helper that accepts a `UUID` or UUID string and returns a `UUID`.

## Runtime API Functions

File: `apps/runtime_api/main.py`

### `create_app(runtime=None)`

Creates the FastAPI Runtime API.

Parameters:

- `runtime`: optional injected `RuntimeExecutionService` for tests.

Behavior:

- stores runtime service in `app.state.runtime`
- registers runtime endpoints

### `health()`

Endpoint: `GET /health`

Returns runtime API health.

### `start_run(request, run_request, tenant_id)`

Endpoint: `POST /agent-runs`

Inputs:

- `request`: FastAPI request object.
- `run_request`: parsed `StartRunRequest`.
- `tenant_id`: from `X-Tenant-ID` header.

Behavior:

1. Get runtime service from app state.
2. Call `RuntimeExecutionService.start_run(...)`.
3. Return `AgentRunResponse`.

### `list_runs(request, tenant_id)`

Endpoint: `GET /agent-runs`

Returns all runs for a tenant.

### `get_run(request, run_id, tenant_id)`

Endpoint: `GET /agent-runs/{run_id}`

Returns one run.

Maps `AgentRunNotFoundError` to HTTP 404.

### `_runtime_from_request(request)`

Private helper.

Returns the runtime service from `request.app.state.runtime`.

## Gateway Services Used

### `RAGPlatformService.retrieve(query, context)`

Returns retrieved context.

Today it returns mock context. Later it will call vector search and knowledge governance.

### `ToolGatewayService.invoke(tool_ref, payload, context)`

Invokes a tool.

Today it echoes the payload. Later it will enforce tool permissions, auditing, and secrets handling.

### `ModelGatewayService.chat(model_profile, messages)`

Calls a model provider abstraction.

Today it returns a mock response. Later it will route to actual models, enforce budgets, and emit token/cost metrics.

## Tests Added

`tests/test_runtime_execution.py` verifies:

- runtime service completes a run
- output contains model, tool, and retrieval sections

`tests/test_runtime_api.py` verifies:

- health endpoint
- start/get/list run endpoints
- tenant scoping

## Learning Point

The Runtime Plane should orchestrate execution without owning every subsystem. It coordinates model gateway, tool gateway, RAG, run history, and later policy/audit/memory/FinOps.
