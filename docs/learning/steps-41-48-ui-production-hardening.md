# Steps 41-48 - UI Completion and Production Hardening

This note explains the final roadmap batch. These steps do not replace the earlier learning docs; they add the UI and production-readiness layer that sits around the platform services.

## Step 41 - Evaluation Workspace UI

File: `apps/control_plane_api/main.py`

Endpoint: `GET /studio/evaluations`

The Evaluation Workspace page is a local browser surface for evaluation suites. In this MVP it is a static page served by the Control Plane API. Its purpose is to show where offline evaluations, online feedback, LLM-as-judge runs, and safety checks will be operated from when the UI becomes fully interactive.

## Step 42 - Deployment Console UI

File: `apps/control_plane_api/main.py`

Endpoint: `GET /studio/deployments`

The Deployment Console page introduces the deployment operator surface. It reflects the enterprise idea that deployment is gated by policy, evaluation, Responsible AI, and AISecOps evidence instead of being a simple push button.

## Step 43 - Authentication and Authorization

Files:

- `services/auth_service/service.py`
- `apps/control_plane_api/main.py`
- `apps/runtime_api/main.py`

Classes:

- `Role`: standard platform roles: admin, developer, and viewer.
- `AuthenticatedPrincipal`: authenticated user or service identity with a tenant and roles.
- `APIKeyAuthService`: small authentication service used to teach the auth boundary.
- `AuthenticationError`: raised when a caller is not authenticated.
- `AuthorizationError`: raised when a caller lacks a required role.

Methods:

- `APIKeyAuthService.authenticate(api_key)`: returns a principal for a valid key and rejects missing or unknown keys.
- `APIKeyAuthService.require_role(principal, required_role)`: enforces role-based authorization, with admin acting as an override role.
- `_configure_optional_api_key_auth(app)`: FastAPI helper that enables `X-API-Key` protection when `AGENTIC_PLATFORM_API_KEY` is configured.

For local learning, auth is optional. If the environment variable is absent, the APIs behave as before. If it is present, non-health API routes require the matching `X-API-Key`.

## Step 44 - Postgres Migration

File: `infrastructure/database/settings.py`

Classes:

- `DatabaseEngine`: identifies SQLite versus Postgres configuration.
- `DatabaseSettings`: normalizes database URL settings and connection pool size.
- `PostgresMigrationPlan`: documents the staged movement from local SQLite repositories to enterprise Postgres repositories.

Methods:

- `DatabaseSettings.from_url(url)`: selects the database engine based on the URL. Postgres URLs keep the production pool size; local SQLite URLs use a single connection.
- `PostgresMigrationPlan.describe()`: returns the migration checklist.

The current platform still runs locally on SQLite. This step freezes the migration contract so future repository implementations can be added cleanly.

## Step 45 - Event Bus Integration

File: `platform_common/events/bus.py`

Classes:

- `PublishedEvent`: one published platform event with topic, payload, event id, and timestamp.
- `EventPublisher`: protocol for future Kafka, Redis Streams, or cloud event bus implementations.
- `InMemoryEventBus`: local test implementation.

Methods:

- `InMemoryEventBus.publish(topic, payload)`: records an event and returns it.
- `InMemoryEventBus.list_events(topic=None)`: lists all events or filters by topic.

This gives the codebase an asynchronous integration seam without forcing Kafka or Redis onto the laptop setup yet.

## Step 46 - Background Workers

File: `services/background_worker/service.py`

Classes:

- `WorkerJobStatus`: queued, completed, and failed lifecycle states.
- `WorkerJob`: one asynchronous job request.
- `BackgroundWorkerService`: local queue runner for background work.

Methods:

- `enqueue(job_type, payload)`: creates a queued job.
- `run_next()`: runs the oldest queued job and marks it completed. In production this would dispatch to a real worker process.
- `list_jobs(status=None)`: lists jobs, optionally filtered by status.

This is the place where long-running evaluation, ingestion, and deployment jobs can move out of HTTP request handling.

## Step 47 - Containerization and Kubernetes

Files:

- `Dockerfile`
- `infrastructure/kubernetes/control-plane-api.yaml`
- `infrastructure/kubernetes/runtime-api.yaml`

The Kubernetes manifests now include service objects, health probes, resource requests and limits, optional API key secret references, and container security contexts. This makes them closer to production deployment manifests while keeping them simple enough to run locally.

## Step 48 - Security Hardening

File: `services/security_hardening/service.py`

Classes:

- `SecurityFinding`: result for one security control.
- `SecurityHardeningService`: runs lightweight platform hardening checks.

Methods:

- `review_runtime_headers(headers)`: checks whether tenant identity and authentication headers are present.

This service is intentionally small. Its value is architectural: security controls become testable platform behavior rather than informal checklist text.

## Verification

The batch adds tests for auth, API protection, database settings, event publishing, worker jobs, security findings, UI pages, and Kubernetes manifest hardening.
