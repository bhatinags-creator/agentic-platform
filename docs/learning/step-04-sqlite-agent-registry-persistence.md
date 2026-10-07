# Step 04 - SQLite Persistence for Agent Registry

## What We Built

We added durable local storage for the Agent Registry using SQLite.

Files:

- `services/agent_registry/sqlite_repository.py`
- `apps/control_plane_api/main.py`
- `tests/test_sqlite_agent_registry_repository.py`
- `.env.example`
- `.gitignore`
- `data/.gitkeep`

## Component Purpose

Before this step, the registry could store agents only in memory. That is good for tests, but data disappears when the process restarts.

SQLite gives your laptop deployment durable data without requiring a database server.

Default database path:

```text
E:\AIProjects\agentic-platform\data\agentic_platform.db
```

## `SQLiteAgentRegistryRepository`

Implements `AgentRegistryRepository` using SQLite.

It stores both queryable columns and full Pydantic JSON payloads.

Why both:

- columns make tenant/name/version lookup easy
- JSON payload preserves the complete domain object

### `__init__(database_path)`

Initializes the repository.

Steps:

1. Convert input path to `Path`.
2. Create the parent folder if needed.
3. Call `_initialize_schema()`.

### `save_agent(agent)`

Persists an `AgentDefinition`.

Behavior:

- inserts a new row if the agent does not exist
- updates the row if the agent already exists
- stores full model JSON in `payload_json`

Returns the same `AgentDefinition`.

### `get_agent(tenant_id, agent_id)`

Loads one tenant-scoped agent.

SQL concept:

- filters by both `tenant_id` and `agent_id`

Returns:

- `AgentDefinition` if found
- `None` if missing

### `find_agent_by_name(tenant_id, name)`

Finds an agent by tenant and case-insensitive name.

Uses generated SQLite column:

- `normalized_name TEXT GENERATED ALWAYS AS (lower(name)) STORED`

This supports duplicate-name checks across restarts.

### `list_agents(tenant_id)`

Loads all agents for one tenant ordered by creation time.

Returns:

- list of `AgentDefinition`

### `save_version(version)`

Persists an `AgentVersion`.

Steps:

1. Verify parent agent exists.
2. Read parent tenant ID.
3. Insert or update version row.
4. Store full version JSON in `payload_json`.

Raises:

- `ValueError` if the parent agent is unknown.

### `get_version(tenant_id, version_id)`

Loads one version by tenant and version ID.

Returns:

- `AgentVersion` if found
- `None` if missing

### `find_version_by_manifest_version(tenant_id, agent_id, manifest_version)`

Finds whether an agent already has the requested manifest version.

This supports `DuplicateAgentVersionError` in the service layer.

### `list_versions(tenant_id, agent_id)`

Lists all versions for a tenant-scoped agent ordered by creation time.

### `_initialize_schema()`

Creates database tables and indexes if they do not exist.

Tables:

- `agents`
- `agent_versions`

Important constraints:

- `agents`: unique `(tenant_id, normalized_name)`
- `agent_versions`: unique `(tenant_id, agent_id, manifest_version)`
- foreign key from versions to agents

### `_connect()`

Opens a SQLite connection.

Behavior:

- sets `row_factory` so rows can be accessed by column name
- enables foreign keys with `PRAGMA foreign_keys = ON`

### `_agent_from_row(row)`

Converts one SQLite row into `AgentDefinition`.

Returns `None` if no row was found.

### `_version_from_row(row)`

Converts one SQLite row into `AgentVersion`.

Returns `None` if no row was found.

## Control Plane Update

`apps/control_plane_api/main.py` gained `build_default_registry()`.

This means normal local API startup uses SQLite automatically, while tests can still inject an in-memory service.

## Tests Added

`tests/test_sqlite_agent_registry_repository.py` verifies:

- agents survive across service instances
- published versions survive across service instances
- duplicate agent names are rejected after restart

## Learning Point

Persistence is an implementation detail behind a repository interface. The service rules did not need to change when storage moved from memory to SQLite.
