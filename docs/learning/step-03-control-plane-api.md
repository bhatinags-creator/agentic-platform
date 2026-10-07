# Step 03 - Control Plane API for Agent Registry

## What We Built

We exposed the Agent Registry through FastAPI.

Files:

- `apps/control_plane_api/main.py`
- `apps/control_plane_api/schemas.py`
- `tests/test_control_plane_api.py`

## Component Purpose

The Control Plane API is the administrative surface of the platform.

It manages agents, versions, lifecycle operations, and later governance/deployment actions.

Runtime execution belongs to the Runtime Plane, not this API.

## Schema Classes in `schemas.py`

### `CreateAgentRequest`

Request body for creating an agent.

Fields:

- `name`: agent display name.
- `owner`: owning team or person.
- `risk_class`: defaults to `medium`.

### `AgentResponse`

Response wrapper for one `AgentDefinition`.

Field:

- `agent`

Why wrapper classes matter: API responses can grow later with metadata without breaking shape.

### `AgentListResponse`

Response wrapper for multiple agents.

Field:

- `agents`

### `PublishAgentVersionRequest`

Request body for publishing an agent version.

Field:

- `manifest`: full `AgentManifest` to publish.

### `AgentVersionResponse`

Response wrapper for one `AgentVersion`.

Field:

- `version`

### `AgentVersionListResponse`

Response wrapper for multiple versions.

Field:

- `versions`

## Functions in `main.py`

### `build_default_registry()`

Creates the default registry service for local deployment.

Behavior:

1. Read `AGENTIC_PLATFORM_DB_PATH`.
2. If absent, use `data/agentic_platform.db`.
3. Create `SQLiteAgentRegistryRepository`.
4. Create `AgentRegistryService` using that repository.

### `create_app(registry=None)`

Builds the FastAPI application.

Parameters:

- `registry`: optional injected `AgentRegistryService`, used by tests.

Behavior:

- stores the registry on `app.state.registry`
- registers all routes
- returns the FastAPI app

### `health()`

Endpoint: `GET /health`

Returns service health.

### `create_agent(request, agent_request, tenant_id)`

Endpoint: `POST /agents`

Inputs:

- `request`: FastAPI request object.
- `agent_request`: parsed `CreateAgentRequest` body.
- `tenant_id`: value from `X-Tenant-ID` header.

Behavior:

1. Fetch registry service from app state.
2. Call `registry_service.create_agent(...)`.
3. Wrap result in `AgentResponse`.
4. Map duplicate errors to HTTP 409.

### `list_agents(request, tenant_id)`

Endpoint: `GET /agents`

Returns all agents for the tenant.

### `get_agent(request, agent_id, tenant_id)`

Endpoint: `GET /agents/{agent_id}`

Returns one agent or 404 if the tenant cannot see it.

### `publish_agent_version(request, agent_id, version_request, tenant_id)`

Endpoint: `POST /agents/{agent_id}/versions`

Behavior:

1. Read manifest from request body.
2. Call `AgentRegistryService.publish_version(...)`.
3. Return `AgentVersionResponse`.
4. Map missing agent to 404 and duplicate version to 409.

### `list_agent_versions(request, agent_id, tenant_id)`

Endpoint: `GET /agents/{agent_id}/versions`

Lists all versions for a tenant-visible agent.

### `deprecate_agent(request, agent_id, tenant_id)`

Endpoint: `POST /agents/{agent_id}/deprecate`

Marks the agent as deprecated.

### `_registry_from_request(request)`

Private helper.

Returns the registry service stored at `request.app.state.registry`.

### `_map_registry_errors(operation)`

Private helper.

Runs a service call and converts domain exceptions into HTTP responses.

Mappings:

- `AgentNotFoundError` -> 404
- `DuplicateAgentNameError` -> 409
- `DuplicateAgentVersionError` -> 409

## Tenant Boundary

All endpoints use `X-Tenant-ID`.

This keeps tenant identity out of the request body and makes it a platform-level request context.

## Tests Added

`tests/test_control_plane_api.py` verifies:

- health endpoint
- create/list agents
- tenant scoping
- duplicate conflict handling
- publish/list versions
- lifecycle promotion
- deprecation

## Learning Point

The API should stay thin. HTTP details live here, but business rules stay in `AgentRegistryService`.
