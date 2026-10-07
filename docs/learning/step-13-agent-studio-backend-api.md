# Step 13 - Agent Studio Backend API

## What We Built

We created the backend foundation for Agent Studio.

Files changed:

- `services/agent_studio/service.py`
- `apps/control_plane_api/main.py`
- `apps/control_plane_api/schemas.py`
- `tests/test_agent_studio.py`
- `tests/test_agent_studio_api.py`

## Component Purpose

Agent Studio is the design-time workspace for enterprise agents.

It will eventually support:

- agent designer
- workflow designer
- prompt editor
- evaluation workspace
- test harness
- deployment console
- cost dashboard

This step creates the first backend workflow: draft an agent, validate it, and publish it into the Agent Registry.

## Agent Studio Service

File: `services/agent_studio/service.py`

### `AgentDraftStatus`

Enum for draft lifecycle.

Values:

- `DRAFT`
- `VALIDATED`
- `PUBLISHED`

### `AgentDraft`

Design-time representation of an agent before it becomes a published registry version.

Fields:

- `draft_id`
- `tenant_id`
- `name`
- `owner`
- `manifest`
- `risk_class`
- `status`
- `agent_id`
- `published_version_id`
- `created_at`
- `updated_at`

### `AgentDraftValidationResult`

Validation response for a draft.

Fields:

- `draft_id`
- `valid`
- `errors`

### `AgentDraftNotFoundError`

Raised when a draft does not exist or is not visible to the tenant.

### `AgentDraftAlreadyPublishedError`

Raised when a caller tries to update or republish a published draft.

### `AgentStudioService`

Coordinates draft design, validation, and publishing.

Methods:

- `__init__(registry)`: stores an `AgentRegistryService` dependency and initializes draft storage.
- `create_draft(...)`: creates a new design-time agent draft.
- `get_draft(tenant_id, draft_id)`: loads one tenant-scoped draft.
- `list_drafts(tenant_id)`: lists drafts for a tenant.
- `update_draft(...)`: updates a non-published draft and resets status to draft.
- `validate_draft(tenant_id, draft_id)`: validates draft and manifest alignment.
- `publish_draft(tenant_id, draft_id)`: creates an agent in the registry and publishes the draft manifest as a version.
- `_validate_manifest_alignment(draft)`: checks design consistency.
- `_parse_uuid(value)`: normalizes UUID input.

## Validation Rules

Current validation checks:

- draft name must match manifest name
- manifest version must be present
- model provider must be present
- model name must be present

These are intentionally simple. Later steps can add policy validation, prompt validation, tool validation, evaluation requirements, and Responsible AI checks.

## Control Plane API Endpoints

File: `apps/control_plane_api/main.py`

New endpoints:

```text
POST /studio/agent-drafts
GET  /studio/agent-drafts
GET  /studio/agent-drafts/{draft_id}
PUT  /studio/agent-drafts/{draft_id}
POST /studio/agent-drafts/{draft_id}/validate
POST /studio/agent-drafts/{draft_id}/publish
```

## API Schema Classes

File: `apps/control_plane_api/schemas.py`

New schemas:

- `CreateAgentDraftRequest`
- `UpdateAgentDraftRequest`
- `AgentDraftResponse`
- `AgentDraftListResponse`
- `AgentDraftValidationResponse`

## Publish Flow

The publish flow is:

1. Agent Studio draft is created.
2. Draft is validated.
3. Agent Registry creates `AgentDefinition`.
4. Agent Registry publishes `AgentVersion`.
5. Draft status becomes `published`.
6. Draft stores `agent_id` and `published_version_id`.

## Tests Added

`tests/test_agent_studio.py` verifies:

- create, validate, and publish draft
- validation errors
- update blocked after publish
- tenant scoping

`tests/test_agent_studio_api.py` verifies:

- API create/list/validate/publish flow
- validation errors through API
- tenant-scoped draft access

## Learning Point

Agent Studio is not just a UI. It needs backend workflow state.

Drafts are design-time objects. Published agents and versions are registry objects. Keeping that separation makes enterprise review, validation, and publishing manageable.
