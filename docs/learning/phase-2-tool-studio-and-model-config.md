# Phase 2 - Tool Studio and Model Configuration

## What this phase adds

Phase 2 turns Tool Studio from a disabled navigation item into a backend-backed module. The user can now register a tool, define implementation metadata, configure schemas, restrict which agents/actions can use it, and run a governed tool test through the Tool Gateway.

Model configuration was already persisted in Settings before this phase. Phase 2 connects that idea with the broader Studio pattern: configuration is stored in the local control-plane database and consumed by agent creation, instead of being hardcoded in the UI.

## Backend files

### `services/tool_gateway/service.py`

`ToolImplementationType`

Defines the type of tool being registered. Current values are `rest`, `openapi`, `mcp`, `python`, and `echo`. `echo` is useful for local validation because it exercises gateway permissions without needing an external service.

`ToolDefinition`

Represents one registered tool. Phase 2 extends it with:

- `implementation_type`: how the tool will be invoked.
- `endpoint_url`: REST/OpenAPI endpoint location when applicable.
- `method`: HTTP method for REST-style tools.
- `auth_type`: authentication style such as none, API key, OAuth2, or mTLS.
- `input_schema`: JSON-schema-like contract for request payloads.
- `output_schema`: JSON-schema-like contract for responses.
- `allowed_agents`: optional allow-list of agent ids.
- `allowed_actions`: optional allow-list of operations such as `read` or `search`.

`ToolRegistryService.register_tool(...)`

Creates or updates a `ToolDefinition` and persists it through the configured repository. The service normalizes `method` to uppercase and converts string values into enum values, so API callers can send simple JSON strings.

`ToolGatewayService.invoke(...)`

Loads the tool by tenant/name, evaluates governance permissions, records the invocation, and returns a structured result. In this phase the gateway returns an echo output for validation, but the call path is the same one agents use.

`ToolGatewayService.evaluate_invocation(...)`

Performs the permission checks:

- inactive tools are denied
- tools with `allowed_agents` reject unlisted agents
- tools with `allowed_actions` reject missing or unsupported actions

### `apps/control_plane_api/schemas.py`

`CreateToolRequest`

Defines the API input for creating/updating tools. It now includes implementation metadata, endpoint/auth settings, schemas, risk, permissions, and timeout.

`TestToolRequest`

Defines the payload for a Tool Studio test run. It carries `agent_id`, optional `action`, and a JSON object payload.

`TestToolResponse`

Wraps the Tool Gateway result returned to the UI.

### `apps/control_plane_api/main.py`

`POST /studio/tools`

Persists a tool definition through `ToolRegistryService.register_tool(...)`.

`GET /studio/tools`

Returns tools stored for the current local workspace tenant. The React UI uses this endpoint to populate the Tool Studio inventory.

`POST /studio/tools/{tool_name}/test`

Runs a selected tool through `ToolGatewayService.invoke(...)`. This matters because Tool Studio is not bypassing governance; it validates the same allowed-agent and allowed-action rules used by runtime execution.

## Frontend files

### `apps/studio_web/src/types.ts`

`ToolImplementationType`

The TypeScript version of the backend implementation type enum.

`ToolDefinition`

The frontend representation of persisted tool records returned by `/studio/tools`.

`StudioBootstrap`

Now includes `tools`, so the app loads agents, drafts, prompts, and tools together on refresh.

### `apps/studio_web/src/lib/api.ts`

`listTools(context)`

Calls `GET /studio/tools` and returns persisted tool records.

`createTool(context, payload)`

Calls `POST /studio/tools` to create or update a tool definition in the local database.

`testTool(context, toolName, payload)`

Calls `POST /studio/tools/{tool_name}/test`. The backend evaluates tool permissions before returning a result.

`loadBootstrap(context)`

Now loads tools alongside agents, drafts, and prompts.

### `apps/studio_web/src/features/tools/ToolStudio.tsx`

`ToolStudio`

The Phase 2 Tool Studio page. It contains:

- registered tool inventory
- create/update tool form
- implementation/auth/schema fields
- allowed agents and allowed actions
- Tool Gateway test runner
- OpenAPI and MCP roadmap panels

`parseJsonObject(value, label)`

Parses JSON textarea values and ensures they are JSON objects. This prevents arrays, strings, or invalid JSON from being sent as tool schemas or test payloads.

`splitCsv(value)`

Converts comma-separated agent/action lists into arrays for the backend.

`formatJson(value)`

Formats Tool Gateway responses for display in the test output panel.

`saveTool()`

Builds the backend request from the form, validates JSON schema fields, calls `createTool(...)`, refreshes persisted app data, and selects the saved tool.

`runToolTest()`

Calls `testTool(...)` with the selected tool, selected agent id, action, and JSON payload. Success and denial both come from the backend path, not from local UI simulation.

### `apps/studio_web/src/components/layout/Shell.tsx`

Tool Studio is now enabled in the sidebar. The footer text was updated to describe the Phase 2 capability.

### `apps/studio_web/src/app/App.tsx`

The app now:

- includes `tools` in empty bootstrap state
- renders `ToolStudio` for the `tools` route
- passes persisted tools and agents into the Tool Studio component

### `apps/studio_web/src/styles.css`

Adds layout styles for:

- three-column Tool Studio workspace
- responsive collapse on smaller screens
- tool detail panel
- bounded test output panel

## Tests

### `tests/test_control_plane_api.py`

`test_studio_asset_apis_create_and_list_backend_records`

Now verifies that tool implementation metadata, endpoint URL, auth type, and schemas round-trip through the backend.

`test_tool_studio_test_runner_uses_gateway_permissions`

Creates a governed tool, verifies an allowed action succeeds, then verifies a disallowed action returns HTTP 403. This proves the UI test runner endpoint is using Tool Gateway governance.

## Current limitation

Phase 2 registers REST/OpenAPI/MCP metadata but does not yet perform external REST calls or import OpenAPI documents. That should be the next backend increment after the UI and permission model are stable.
