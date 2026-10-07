# Project File, Class, and Method Guide

This guide is the running map of the Agentic Platform codebase. Use it when you want to understand what each component owns, which class to change, and how the pieces call each other.

## Current Learning Steps

- Step 01: Platform contracts and domain models.
- Step 02: Agent Registry service and repository interface.
- Step 03: Control Plane API for registry operations.
- Step 04: SQLite persistence for local durable registry storage.
- Step 05: Runtime Plane execution path.
- Step 06: Runtime policy gate and audit trail.
- Step 07: AI FinOps cost governance.
- Step 08: Memory governance runtime integration.
- Steps 09-12: Persistent runtime, audit, FinOps, and memory stores.
- Step 13: Agent Studio backend API.
- Steps 14-22: Prompt management, Agent Studio test harness, evaluation architecture, Responsible AI, and runtime Responsible AI hooks.

## Root Files

### `README.md`

Explains how to start the project locally and where the frozen design documents live.

### `pyproject.toml`

Defines the Python package, dependencies, test configuration, and Ruff line length.

### `.env.example`

Documents local environment variables. Important value:

- `AGENTIC_PLATFORM_DB_PATH`: SQLite file used by the Control Plane Agent Registry.

### `.gitignore`

Prevents local generated files from being committed, including virtual environments, caches, and generated SQLite database files under `data/`.

## Platform Domain Models

File: `platform_common/domain/models.py`

This file defines the shared language of the platform. API services, runtime services, governance services, tests, and future UI code should use these contracts instead of inventing duplicate shapes.

### Enum Classes

#### `LifecycleStatus`

Represents where an enterprise platform object is in its lifecycle.

Values:

- `DRAFT`: created but not approved or published.
- `VALIDATED`: passed validation checks.
- `PUBLISHED`: available for deployment or use.
- `DEPLOYED`: actively deployed.
- `DEPRECATED`: should not be used for new deployments.
- `RETIRED`: removed from active operation.

#### `RiskClass`

Business risk level of an agent or workflow.

Values: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`.

This will later drive approvals, audit depth, policy checks, and deployment gates.

#### `DataClassification`

Classification of data an agent can handle.

Values: `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED`.

This is important for governance and model routing.

#### `FrameworkType`

The implementation framework behind an agent.

Values include `LANGGRAPH`, `LANGCHAIN`, `CREWAI`, `AUTOGEN`, `SEMANTIC_KERNEL`, `LLAMAINDEX`, and `CUSTOM_PYTHON`.

The platform remains framework-neutral by storing this as metadata instead of making framework classes core domain objects.

#### `RetentionPolicy`

Memory/data retention policy enum.

Values:

- `RUNTIME_ONLY`
- `HOURS_24`
- `DAYS_90`
- `YEARS_7`
- `POLICY_CONTROLLED`

Used by memory governance.

#### `AgentRunStatus`

Execution status for one agent run.

Values:

- `QUEUED`
- `RUNNING`
- `WAITING_FOR_HUMAN`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

### Model Classes

#### `ResourceRef`

A versioned pointer to another platform-managed resource.

Fields:

- `ref`: logical reference, for example `tool.customer-profile-api`.
- `version`: optional version string.
- `required`: whether execution should fail if the resource is unavailable.

Why it exists: agents should reference tools, knowledge bases, policies, and sub-agents without embedding implementation details.

#### `ModelProfile`

Describes which model should be used.

Fields:

- `provider`: model provider name, such as `mock`, `openai`, or future enterprise providers.
- `model`: concrete model name.
- `profile_ref`: optional managed profile reference.
- `parameters`: model settings.
- `data_classification_allowed`: data classifications this model profile can process.

#### `MemoryPolicy`

Defines memory retention defaults for an agent.

Fields:

- `session`: defaults to 24 hours.
- `conversation`: defaults to 90 days.
- `agent_working_memory`: defaults to runtime only.
- `semantic_memory`: defaults to policy controlled.
- `human_decisions`: defaults to 7 years.

#### `ExecutionPolicy`

Controls runtime limits.

Fields:

- `max_iterations`
- `max_depth`
- `timeout_seconds`
- `max_cost`
- `max_tokens`

This will later prevent runaway agents.

#### `HumanApprovalPolicy`

Defines whether human approval is needed.

Fields:

- `required`
- `policy_ref`
- `checkpoint_before_wait`
- `approval_modes`

#### `ObservabilityPolicy`

Defines what runtime information should be captured.

Fields:

- `tracing_required`
- `audit_required`
- `capture_prompts`
- `capture_outputs`

#### `EvaluationPolicy`

Defines evaluation requirements before deployment.

Fields:

- `required_eval_suite`
- `minimum_score`
- `block_deployment_on_failure`

#### `AgentManifest`

The complete behavior package for a versioned agent.

Key fields:

- `id`, `name`, `version`
- `role`, `goal`, `description`
- `model`
- `framework`
- `data_classification`
- `skills`, `tools`, `knowledge`, `policies`, `guardrails`, `sub_agents`
- `memory`, `execution`, `human_approval`, `observability`, `evaluation`
- `metadata`

Method:

- `agent_id_must_be_canonical(value)`: Pydantic validator that rejects manifest IDs containing spaces. This keeps IDs stable for APIs, deployment, and references.

#### `AgentDefinition`

The long-lived identity of an agent.

Fields:

- `agent_id`
- `tenant_id`
- `name`
- `owner`
- `risk_class`
- `status`
- `created_at`

Concept: an agent definition can have many published versions.

#### `AgentVersion`

One immutable published version of an agent manifest.

Fields:

- `version_id`
- `agent_id`
- `manifest`
- `status`
- `checksum`
- `created_at`

Concept: deployment should target a specific version, not a mutable agent name.

#### `AgentRun`

One execution attempt of an agent version.

Fields:

- `run_id`
- `tenant_id`
- `agent_id`
- `agent_version`
- `user_id`
- `trace_id`
- `input`
- `status`
- `output`
- `created_at`

#### `PolicyDecision`

Represents an allow/deny decision from the policy layer.

Fields:

- `decision_id`
- `decision`
- `constraints`
- `reason`

## Agent Registry

Files:

- `services/agent_registry/service.py`
- `services/agent_registry/sqlite_repository.py`

### `AgentRegistryError`

Base exception for Agent Registry domain errors.

### `AgentNotFoundError`

Raised when an agent does not exist for the requested tenant.

### `DuplicateAgentNameError`

Raised when a tenant tries to create two agents with the same case-insensitive name.

### `DuplicateAgentVersionError`

Raised when an agent already has the same manifest version.

### `AgentRegistryRepository`

Abstract storage interface for the registry.

Methods:

- save_agent(agent)`: persists an `AgentDefinition` and returns it.
- `get_agent(tenant_id, agent_id)`: returns one tenant-scoped agent or `None`.
- `find_agent_by_name(tenant_id, name)`: finds an agent by tenant and case-insensitive name.
- `list_agents(tenant_id)`: returns all agents for a tenant.
- `save_version(version)`: persists an `AgentVersion` and returns it.
- `get_version(tenant_id, version_id)`: returns a tenant-scoped version or `None`.
- `find_version_by_manifest_version(tenant_id, agent_id, manifest_version)`: finds duplicate versions.
- `list_versions(tenant_id, agent_id)`: lists all versions for one agent.

Concept: the service depends on this interface, not on a specific database.

### `InMemoryAgentRegistryRepository`

Dictionary-backed implementation used for unit tests and isolated API tests.

Methods:

- `__init__()`: creates internal `_agents` and `_versions` dictionaries.
- `save_agent(agent)`: stores the agent by UUID.
- `get_agent(tenant_id, agent_id)`: returns only if tenant matches.
- `find_agent_by_name(tenant_id, name)`: uses `casefold()` for case-insensitive duplicate detection.
- `list_agents(tenant_id)`: returns tenant agents sorted by creation time.
- `save_version(version)`: stores the version by UUID.
- `get_version(tenant_id, version_id)`: returns only if the version belongs to a tenant-visible agent.
- `find_version_by_manifest_version(...)`: checks duplicate manifest versions for an agent.
- `list_versions(tenant_id, agent_id)`: lists versions for a tenant-scoped agent.

### `AgentRegistryService`

Business logic for registry workflows.

Methods:

- `__init__(repository=None)`: accepts a repository or defaults to in-memory storage.
- `create_agent(tenant_id, name, owner, risk_class)`: validates duplicate names, creates `AgentDefinition`, saves it.
- `get_agent(tenant_id, agent_id)`: parses UUID, enforces tenant scope, raises `AgentNotFoundError` if absent.
- `list_agents(tenant_id)`: delegates tenant-scoped listing to repository.
- `publish_version(tenant_id, agent_id, manifest)`: validates agent exists, blocks duplicate manifest version, creates checksum, saves `AgentVersion`, promotes draft agent to published.
- `list_versions(tenant_id, agent_id)`: validates agent exists, then lists versions.
- `deprecate_agent(tenant_id, agent_id)`: marks agent as deprecated.
- `_manifest_checksum(manifest)`: creates SHA-256 checksum from manifest JSON.
- `_parse_uuid(value)`: accepts UUID or string and returns UUID.

### `SQLiteAgentRegistryRepository`

SQLite-backed repository for durable local laptop deployment.

Methods:

- `__init__(database_path)`: stores DB path, creates parent folder, initializes schema.
- `save_agent(agent)`: upserts an agent row and stores full JSON payload.
- `get_agent(tenant_id, agent_id)`: loads one agent from SQLite.
- `find_agent_by_name(tenant_id, name)`: uses SQLite generated `normalized_name` to find case-insensitive duplicate names.
- `list_agents(tenant_id)`: loads all tenant agents ordered by creation time.
- `save_version(version)`: validates parent agent exists, then upserts version row.
- `get_version(tenant_id, version_id)`: loads a tenant-scoped version.
- `find_version_by_manifest_version(...)`: finds duplicate manifest version for one agent.
- `list_versions(tenant_id, agent_id)`: loads all versions for an agent.
- `_initialize_schema()`: creates `agents` and `agent_versions` tables and indexes.
- `_connect()`: opens SQLite connection, enables row access by name and foreign keys.
- `_agent_from_row(row)`: converts SQLite row JSON to `AgentDefinition`.
- `_version_from_row(row)`: converts SQLite row JSON to `AgentVersion`.

## Control Plane API

Files:

- `apps/control_plane_api/main.py`
- `apps/control_plane_api/schemas.py`

### API Schema Classes

#### `CreateAgentRequest`

Request body for `POST /agents`.

Fields:

- `name`
- `owner`
- `risk_class`

#### `AgentResponse`

Response wrapper containing one `AgentDefinition`.

#### `AgentListResponse`

Response wrapper containing a list of `AgentDefinition` objects.

#### `PublishAgentVersionRequest`

Request body for publishing a version.

Field:

- `manifest`

#### `AgentVersionResponse`

Response wrapper containing one `AgentVersion`.

#### `AgentVersionListResponse`

Response wrapper containing a list of `AgentVersion` objects.

### Control Plane Functions

#### `build_default_registry()`

Builds the default production-like local registry service using `SQLiteAgentRegistryRepository`.

Reads `AGENTIC_PLATFORM_DB_PATH`; if missing, uses `data/agentic_platform.db`.

#### `create_app(registry=None)`

Creates the FastAPI app. Allows tests to inject an in-memory registry while normal local use gets SQLite.

Endpoint functions inside it:

- `health()`: returns service health.
- `create_agent(request, agent_request, tenant_id)`: handles `POST /agents`.
- `list_agents(request, tenant_id)`: handles `GET /agents`.
- `get_agent(request, agent_id, tenant_id)`: handles `GET /agents/{agent_id}`.
- `publish_agent_version(request, agent_id, version_request, tenant_id)`: handles `POST /agents/{agent_id}/versions`.
- `list_agent_versions(request, agent_id, tenant_id)`: handles `GET /agents/{agent_id}/versions`.
- `deprecate_agent(request, agent_id, tenant_id)`: handles `POST /agents/{agent_id}/deprecate`.

#### `_registry_from_request(request)`

Fetches `AgentRegistryService` from `request.app.state.registry`.

#### `_map_registry_errors(operation)`

Converts service-layer exceptions into HTTP errors:

- `AgentNotFoundError` -> 404
- duplicate errors -> 409

## Runtime Plane

Files:

- `services/runtime_execution/service.py`
- `apps/runtime_api/main.py`
- `apps/runtime_api/schemas.py`

### Runtime Schema Classes

#### `StartRunRequest`

Request body for `POST /agent-runs`.

Fields:

- `user_id`
- `agent_id`
- `agent_version`
- `input`

Tenant is intentionally not in the body. It comes from `X-Tenant-ID`.

#### `AgentRunResponse`

Response wrapper containing one `AgentRun`.

#### `AgentRunListResponse`

Response wrapper containing a list of `AgentRun` objects.

### `AgentRunNotFoundError`

Raised when a run cannot be found for the requested tenant.

### `AgentRunRepository`

Abstract storage interface for runtime execution history.

Methods:

- `save_run(run)`: persists and returns an `AgentRun`.
- `get_run(tenant_id, run_id)`: returns one tenant-scoped run or `None`.
- `list_runs(tenant_id)`: returns all runs for a tenant.

### `InMemoryAgentRunRepository`

Dictionary-backed runtime run store.

Methods:

- `__init__()`: creates internal `_runs` dictionary.
- `save_run(run)`: stores the run by UUID.
- `get_run(tenant_id, run_id)`: returns only if tenant matches.
- `list_runs(tenant_id)`: returns tenant runs sorted by creation time.

### `RuntimeExecutionService`

Coordinates one MVP agent execution.

Methods:

- `__init__(repository=None, model_gateway=None, tool_gateway=None, rag_platform=None)`: accepts dependencies or creates defaults.
- `start_run(tenant_id, user_id, agent_id, agent_version, input_payload)`: creates a running run, calls RAG, tool, and model gateways, marks run completed, stores output.
- `get_run(tenant_id, run_id)`: loads a tenant-scoped run or raises `AgentRunNotFoundError`.
- `list_runs(tenant_id)`: lists runs for a tenant.
- `_parse_uuid(value)`: accepts UUID or string and returns UUID.

### Runtime API Functions

#### `create_app(runtime=None)`

Creates the Runtime FastAPI app. Allows tests to inject a runtime service.

Endpoint functions inside it:

- `health()`: returns runtime service health.
- `start_run(request, run_request, tenant_id)`: handles `POST /agent-runs`, starts execution, returns run.
- `list_runs(request, tenant_id)`: handles `GET /agent-runs`.
- `get_run(request, run_id, tenant_id)`: handles `GET /agent-runs/{run_id}` and maps missing runs to 404.

#### `_runtime_from_request(request)`

Fetches `RuntimeExecutionService` from `request.app.state.runtime`.

## Gateway Services

### `ModelGatewayService`

File: `services/model_gateway/service.py`

Methods:

- `chat(model_profile, messages)`: returns a mock `ModelInvocationResult`. Later this becomes routing, quota, safety, and model provider integration.

### `ModelInvocationResult`

Dataclass returned by model calls.

Fields:

- `output_text`
- `provider`
- `model`
- `prompt_tokens`
- `completion_tokens`
- `estimated_cost`

### `ToolGatewayService`

File: `services/tool_gateway/service.py`

Methods:

- `invoke(tool_ref, payload, context)`: returns a mock tool result with echo output and audit marker.

### `RAGPlatformService`

File: `services/rag_platform/service.py`

Methods:

- `retrieve(query, context)`: returns mock retrieved context with citation metadata.

## Key Learning Thread

The platform is being built in layers:

1. Domain contracts define common language.
2. Services enforce business rules.
3. Repositories hide persistence details.
4. APIs expose platform capabilities over HTTP.
5. Runtime orchestration coordinates gateways and records execution.
6. Policy and audit add enterprise control and evidence.
7. FinOps records AI usage and cost for governance.
8. Memory governance classifies records and enforces retention metadata.
9. Agent Studio supports design-time draft, validation, publish, and test workflows.
10. Prompt management treats prompts as governed, versioned assets.
11. Evaluation services turn quality, safety, and feedback into measurable evidence.
12. Responsible AI services capture fairness, bias, explainability, model risk, and regulatory evidence.

This structure lets us grow the system step by step without mixing every concern into one file.
## Policy and Audit

Files:

- `services/policy_engine/service.py`
- `services/audit_service/service.py`

### `PolicyEngineService`

Evaluates whether a platform action should be allowed.

Methods:

- `evaluate(action, subject, resource)`: returns a `PolicyDecision`. The current MVP denies when runtime input contains `policy_decision: deny`; otherwise it permits.

### `AuditService`

Records platform events as `EventEnvelope` objects.

Methods:

- `__init__()`: creates the in-memory `records` list.
- `write(event)`: appends and returns an audit event.
- `list_events(tenant_id=None, trace_id=None)`: filters audit events by tenant and trace.

### Runtime Policy/Audit Integration

`RuntimeExecutionService` now uses `PolicyEngineService` before model/tool/RAG work.

It writes audit events for:

- `agent_run.started`
- `agent_run.policy_evaluated`
- `agent_run.completed`
- `agent_run.denied`

`RuntimePolicyDeniedError` carries the failed run and policy decision so the API can return a clear `403 Forbidden` response.
## AI FinOps

File:

- `services/finops_service/service.py`

### `CostEvent`

Immutable dataclass for one model usage cost record.

Fields include tenant, agent, run, trace, workflow, department, model provider, model name, token counts, estimated cost, and timestamp.

### `CostSummary`

Aggregated tenant usage and cost summary.

Fields:

- `tenant_id`
- `total_runs`
- `total_prompt_tokens`
- `total_completion_tokens`
- `total_tokens`
- `total_cost`

### `BudgetExceededError`

Raised when recording usage would exceed a tenant budget.

### `AIFinOpsService`

Tracks AI model usage and estimated cost.

Methods:

- `__init__()`: creates in-memory cost event and budget stores.
- `set_tenant_budget(tenant_id, budget)`: configures a tenant budget.
- `record_model_usage(...)`: records one model usage event and enforces budget.
- `list_events(...)`: filters events by tenant, agent, run, or department.
- `summarize_tenant(tenant_id)`: returns aggregate usage for a tenant.
- `total_cost_by_tenant(tenant_id)`: returns tenant spend.
- `total_cost_by_agent(tenant_id, agent_id)`: returns spend by agent.
- `total_cost_by_department(tenant_id, department)`: returns spend by department.

### Runtime FinOps Integration

`RuntimeExecutionService` records a cost event after each model call and places a `finops` section in run output.

It also writes an `agent_run.cost_recorded` audit event.
## Memory Governance

File:

- `services/memory_governance/service.py`

### `MemoryType`

Enum for governed memory categories: session, conversation, agent working memory, semantic memory, and human decisions.

### `MemoryRecord`

Immutable dataclass for one governed memory record.

Fields include tenant, agent, run, trace, memory type, retention policy, content, creation time, expiry time, and optional policy reference.

### `MemoryGovernanceService`

Owns memory retention behavior.

Methods:

- `__init__()`: creates the in-memory record store.
- `retention_for(memory_type)`: returns default retention for a memory category.
- `create_record(...)`: creates a governed memory record with calculated retention and expiry.
- `list_records(...)`: filters records by tenant, agent, run, and memory type.
- `purge_expired(now=None)`: removes expired records.
- `_parse_memory_type(memory_type)`: normalizes string/enum memory type input.
- `_expires_at(created_at, retention)`: calculates automatic expiry based on retention policy.

### Runtime Memory Integration

`RuntimeExecutionService` records conversation memory for completed runs and adds a `memory` section to run output.

It also writes an `agent_run.memory_recorded` audit event.
## Agent Studio

Files:

- `services/agent_studio/service.py`
- `apps/control_plane_api/main.py`
- `apps/control_plane_api/schemas.py`

### `AgentDraftStatus`

Draft lifecycle enum: draft, validated, published.

### `AgentDraft`

Design-time agent object used before publishing into the Agent Registry.

### `AgentDraftValidationResult`

Validation result containing draft id, validity flag, and errors.

### `AgentStudioService`

Methods:

- `create_draft(...)`: creates an Agent Studio draft.
- `get_draft(tenant_id, draft_id)`: loads a tenant-scoped draft.
- `list_drafts(tenant_id)`: lists tenant drafts.
- `update_draft(...)`: updates a non-published draft.
- `validate_draft(tenant_id, draft_id)`: validates draft and manifest alignment.
- `publish_draft(tenant_id, draft_id)`: creates registry agent and version from draft.
- `_validate_manifest_alignment(draft)`: checks draft consistency.
- `_parse_uuid(value)`: normalizes UUID input.

### Agent Studio API

Endpoints:

- `POST /studio/agent-drafts`
- `GET /studio/agent-drafts`
- `GET /studio/agent-drafts/{draft_id}`
- `PUT /studio/agent-drafts/{draft_id}`
- `POST /studio/agent-drafts/{draft_id}/validate`
- `POST /studio/agent-drafts/{draft_id}/publish`



## Prompt Management

File:

- `services/prompt_management/service.py`

### `PromptTemplateStatus`

Lifecycle enum for prompt assets: draft, published, and deprecated.

### `PromptTemplate`

Metadata for a prompt family. It stores tenant ownership, name, description, owner, status, and creation time.

### `PromptVersion`

A concrete version of prompt text. It stores the template text, extracted variables, semantic version label, and publication status.

### `PromptRenderResult`

Returned by prompt rendering. It contains the rendered prompt text and the variables used to produce it.

### `PromptTemplateNotFoundError`

Raised when a prompt template does not exist for the requested tenant.

### `PromptVersionNotFoundError`

Raised when a prompt version is missing or its parent template is not tenant-visible.

### `PromptValidationError`

Raised when required prompt variables are not supplied.

### `PromptManagementService`

Methods:

- `__init__()`: creates in-memory prompt template and version stores.
- `create_template(...)`: creates prompt template metadata.
- `create_version(...)`: creates versioned prompt text and extracts placeholders.
- `publish_version(...)`: marks a version and its parent template as published.
- `render(...)`: validates variables and renders final prompt text.
- `get_template(...)`: loads a tenant-scoped template.
- `get_version(...)`: loads a tenant-scoped version through its parent template.
- `list_templates(...)`: lists prompt templates for a tenant.
- `_extract_variables(...)`: finds `{variable}` placeholders using Python's formatter parser.
- `_parse_uuid(...)`: normalizes UUID input.

## Agent Studio Test Harness

File:

- `services/agent_studio/service.py`

### `AgentTestStatus`

Enum for test harness outcome: passed or failed.

### `AgentTestCase`

One draft test case with a name, input payload, and optional expected text.

### `AgentTestRunResult`

Result of running the harness. It stores the draft id, status, checked case count, failures, and timestamp.

### Additional `AgentStudioService` Methods

- `run_test_harness(...)`: validates a draft, normalizes test cases, simulates output, checks expectations, and stores a test run result.
- `_simulate_test_output(...)`: creates deterministic local output from the draft role, goal, and test input.

## Evaluation Service

File:

- `services/evaluation_service/service.py`

### `EvaluationMode`

Enum for offline, online, LLM-as-judge, and safety evaluations.

### `EvaluationStatus`

Enum for passed, failed, and completed outcomes.

### `SafetyMetric`

Enum for hallucination, groundedness, toxicity, PII leakage, and prompt injection resilience.

### `EvaluationCase`

One evaluation input with optional expected output or expected facts.

### `EvaluationSuite`

Collection of evaluation cases for one tenant and evaluation mode.

### `EvaluationScore`

One metric score with numeric value, pass/fail flag, and optional reason.

### `EvaluationResult`

Result record for one evaluation run against an agent version.

### `OnlineFeedback`

User or human scoring record attached to a runtime run.

### `EvaluationService`

Methods:

- `__init__()`: creates in-memory suites, results, and feedback stores.
- `create_suite(...)`: creates an evaluation suite.
- `run_offline_evaluation(...)`: runs the original simple offline evaluation contract and stores a structured result.
- `run_suite(...)`: scores suite cases and returns an aggregate pass/fail result.
- `record_online_feedback(...)`: records user or human feedback.
- `score_with_llm_judge(...)`: simulates judge scoring with deterministic local logic.
- `run_safety_evaluation(...)`: checks output against safety metrics.
- `_get_suite(...)`: loads a tenant-scoped suite.
- `_score_case(...)`: scores one evaluation case.

## Responsible AI

File:

- `services/responsible_ai/service.py`

### `ResponsibleAIStatus`

Enum for passed, review required, failed, and registered states.

### `FairnessTestResult`

Fairness metric result for an agent.

### `BiasDetectionResult`

Sensitive-attribute bias detection result.

### `ExplainabilityReport`

Explainability summary with supporting evidence.

### `ModelRiskRecord`

Model risk registration record for a model profile and use case.

### `RegulatoryEvidenceRecord`

Compliance evidence record with a typed payload.

### `ResponsibleAIAssessment`

Runtime Responsible AI assessment attached to a run.

### `ResponsibleAIService`

Methods:

- `__init__()`: creates in-memory stores for all Responsible AI evidence types.
- `create_model_risk_record(...)`: registers model risk for a profile and use case.
- `run_fairness_test(...)`: records fairness score and marks weak results for review.
- `detect_bias(...)`: checks output for sensitive attribute references.
- `create_explainability_report(...)`: stores an explainability report.
- `generate_regulatory_evidence(...)`: creates compliance evidence.
- `assess_runtime_output(...)`: runs simple runtime Responsible AI checks and returns an assessment.

### Runtime Responsible AI Integration

`RuntimeExecutionService` now calls `ResponsibleAIService.assess_runtime_output(...)` for completed runs.

It adds this output section:

- `responsible_ai.status`
- `responsible_ai.findings`

It also writes this audit event:

- `agent_run.responsible_ai_checked`

## AISecOps

File:

- `services/aisecops/service.py`

### `AISecOpsSignalType`

Enum for AI security monitoring categories: prompt attack, agent behavior, RAG poisoning, model drift, tool abuse, and anomaly.

### `AISecOpsSeverity`

Enum for severity levels: none, low, medium, high, and critical.

### `AISecOpsStatus`

Enum for investigation lifecycle: open, investigating, mitigated, and false positive.

### `AISecOpsSignal`

Base security signal record with tenant, agent, signal type, severity, evidence, run, trace, status, and timestamp fields.

### Specialized AISecOps Records

- `PromptAttackMonitoringRecord`: records prompt attack terms.
- `AgentBehaviorMonitoringRecord`: records suspicious agent behavior.
- `RAGPoisoningMonitoringRecord`: records suspicious knowledge source signals.
- `ModelDriftMonitoringRecord`: records drift score and baseline evidence.
- `ToolAbuseMonitoringRecord`: records suspicious tool usage.
- `AnomalyDetectionRecord`: records general anomaly score and evidence.

### `AISecOpsSummary`

Tenant-level aggregate counts for total, open, critical, high, and by-type signals.

### `AISecOpsSignalNotFoundError`

Raised when a signal is missing or belongs to another tenant.

### `AISecOpsMonitoringService`

Methods:

- `__init__()`: creates the in-memory signal store.
- `inspect_prompt(...)`: scans prompt text and records prompt attack signals.
- `record_prompt_attack(...)`: creates prompt attack records.
- `record_agent_behavior(...)`: creates suspicious behavior records.
- `record_rag_poisoning(...)`: creates RAG poisoning records.
- `record_model_drift(...)`: creates model drift records.
- `record_tool_abuse(...)`: creates tool abuse records.
- `record_anomaly(...)`: creates anomaly records.
- `list_signals(...)`: returns tenant-scoped signals with optional filters.
- `update_signal_status(...)`: changes signal investigation status.
- `summarize_tenant(...)`: returns tenant AISecOps summary metrics.
- `_save(...)`: stores a signal.
- `_severity_from_score(...)`: maps scores to severity.
- `_parse_uuid(...)`: normalizes UUID input.
