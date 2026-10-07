# Step 02 - Persistent Agent Registry

## What We Built

We created the Agent Registry service layer in:

- `services/agent_registry/service.py`
- `tests/test_agent_registry.py`

This step introduced the repository pattern and the business rules for registering agents and publishing versions.

## Component Purpose

The Agent Registry is the source of truth for enterprise agents.

It answers:

- Which agents exist for a tenant?
- Who owns each agent?
- What lifecycle state is each agent in?
- Which versions have been published?
- Is a new version allowed?

## Error Classes

### `AgentRegistryError`

Base exception for all registry-specific domain errors.

It gives future callers one parent type to catch if they want to handle all registry problems together.

### `AgentNotFoundError`

Raised when a requested agent does not exist for the given tenant.

This matters because an agent may exist in one tenant but must still be invisible to another tenant.

### `DuplicateAgentNameError`

Raised when a tenant tries to create two agents with the same name.

The check is case-insensitive, so `Claims Agent` and `claims agent` conflict within the same tenant.

### `DuplicateAgentVersionError`

Raised when the same manifest version is published twice for one agent.

This protects the immutability of published versions.

## `AgentRegistryRepository`

Abstract storage contract used by `AgentRegistryService`.

The service owns business rules. The repository owns storage details.

### `save_agent(agent)`

Persists an `AgentDefinition`.

Input:

- `agent`: the domain model to store.

Returns:

- the saved `AgentDefinition`.

### `get_agent(tenant_id, agent_id)`

Loads one agent by tenant and ID.

Returns:

- `AgentDefinition` if found and tenant matches.
- `None` if missing or not tenant-visible.

### `find_agent_by_name(tenant_id, name)`

Finds an agent by tenant and name.

Used before creation to enforce duplicate-name rules.

### `list_agents(tenant_id)`

Returns all agents owned by a tenant.

### `save_version(version)`

Persists an `AgentVersion`.

### `get_version(tenant_id, version_id)`

Loads a version only if it belongs to an agent visible to the tenant.

### `find_version_by_manifest_version(tenant_id, agent_id, manifest_version)`

Finds whether a manifest version already exists for an agent.

Used to block duplicate publication.

### `list_versions(tenant_id, agent_id)`

Lists all published versions for a tenant-scoped agent.

## `InMemoryAgentRegistryRepository`

Development and test implementation of `AgentRegistryRepository`.

It uses dictionaries instead of a database.

### `__init__()`

Creates two dictionaries:

- `_agents`: stores `AgentDefinition` by agent UUID.
- `_versions`: stores `AgentVersion` by version UUID.

### `save_agent(agent)`

Stores the agent in `_agents` using `agent.agent_id` as the key.

### `get_agent(tenant_id, agent_id)`

Looks up the agent by ID, then checks tenant ownership.

Returns `None` when the tenant does not match.

### `find_agent_by_name(tenant_id, name)`

Normalizes the requested name using `casefold()` and scans stored agents.

### `list_agents(tenant_id)`

Filters agents by tenant and sorts them by `created_at`.

### `save_version(version)`

Stores the version in `_versions` using `version.version_id` as the key.

### `get_version(tenant_id, version_id)`

Loads the version, then verifies the parent agent is tenant-visible.

### `find_version_by_manifest_version(...)`

Scans versions and returns a version whose `agent_id` and `manifest.version` match.

### `list_versions(tenant_id, agent_id)`

Returns versions for the requested agent only if the agent belongs to that tenant.

## `AgentRegistryService`

Business service that coordinates registry workflows.

### `__init__(repository=None)`

Accepts a repository implementation.

If none is passed, it uses `InMemoryAgentRegistryRepository`.

This makes the service easy to test and easy to switch to SQLite/Postgres.

### `create_agent(tenant_id, name, owner, risk_class)`

Creates a new `AgentDefinition`.

Steps:

1. Check if the tenant already has an agent with the same name.
2. Raise `DuplicateAgentNameError` if duplicate exists.
3. Build an `AgentDefinition`.
4. Save it through the repository.

Returns:

- the saved `AgentDefinition`.

### `get_agent(tenant_id, agent_id)`

Loads one agent.

Steps:

1. Convert string IDs into UUIDs.
2. Ask repository for tenant-scoped agent.
3. Raise `AgentNotFoundError` if absent.
4. Return the agent.

### `list_agents(tenant_id)`

Returns all agents visible to a tenant.

### `publish_version(tenant_id, agent_id, manifest)`

Publishes a new `AgentVersion`.

Steps:

1. Parse agent ID.
2. Verify the agent exists for the tenant.
3. Check whether the manifest version already exists.
4. Create an `AgentVersion` with status `published`.
5. Generate a checksum for the manifest.
6. Save the version.
7. Promote the agent from `draft` to `published` if this is its first publish.

Returns:

- saved `AgentVersion`.

### `list_versions(tenant_id, agent_id)`

Validates the agent exists, then returns all versions for it.

### `deprecate_agent(tenant_id, agent_id)`

Marks an agent as deprecated.

Useful when an agent should no longer be used for new deployments.

### `_manifest_checksum(manifest)`

Private helper.

Converts the manifest to JSON and hashes it with SHA-256.

Why: checksums help prove exactly which manifest content was published.

### `_parse_uuid(value)`

Private helper.

Accepts either a `UUID` object or UUID string and returns a `UUID`.

## Tests Added

`tests/test_agent_registry.py` verifies:

- duplicate names are rejected within a tenant
- same names are allowed across tenants
- publishing validates the agent
- publishing promotes lifecycle state
- duplicate manifest versions are rejected
- tenant boundaries are enforced

## Learning Point

The service is where rules live. The repository is where data lives. Keeping those separate is one of the most important enterprise architecture habits.
