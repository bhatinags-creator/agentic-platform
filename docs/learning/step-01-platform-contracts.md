# Step 01 - Platform Contracts

## What We Built

We created the shared domain contracts in:

- `platform_common/domain/models.py`
- `platform_common/events/envelope.py`

These contracts are the common language used by APIs, services, tests, deployment, governance, and runtime components.

## Why Contracts Come First

In enterprise platforms, teams need stable terms before implementation becomes large. If every service invents its own shape for agent, version, memory, policy, or run, the system becomes hard to integrate.

Contracts make the platform understandable and testable.

## Classes in `platform_common/domain/models.py`

### `LifecycleStatus`

Enum for object lifecycle: `draft`, `validated`, `published`, `deployed`, `deprecated`, `retired`.

Used by agents and versions to show whether they are still editable, available, deployed, or retired.

### `RiskClass`

Enum for business risk: `low`, `medium`, `high`, `critical`.

Later this will drive approvals, model restrictions, audit depth, and deployment rules.

### `DataClassification`

Enum for data sensitivity: `public`, `internal`, `confidential`, `restricted`.

Used by model routing, policy checks, and governance.

### `FrameworkType`

Enum for agent implementation framework.

Examples: LangGraph, LangChain, CrewAI, AutoGen, Semantic Kernel, LlamaIndex, custom Python.

The platform stores the framework type as metadata so the core remains framework-neutral.

### `RetentionPolicy`

Enum for memory retention.

Examples: runtime only, 24 hours, 90 days, 7 years, policy controlled.

### `ResourceRef`

A versioned pointer to another platform resource.

Fields:

- `ref`
- `version`
- `required`

Used for tools, knowledge bases, guardrails, policies, sub-agents, and skills.

### `ModelProfile`

Describes which model to use.

Fields:

- `provider`
- `model`
- `profile_ref`
- `parameters`
- `data_classification_allowed`

### `MemoryPolicy`

Defines default memory retention per memory type.

Fields:

- `session`
- `conversation`
- `agent_working_memory`
- `semantic_memory`
- `human_decisions`

### `ExecutionPolicy`

Runtime guardrails for execution.

Fields:

- `max_iterations`
- `max_depth`
- `timeout_seconds`
- `max_cost`
- `max_tokens`

### `HumanApprovalPolicy`

Describes whether a human must approve execution or decision points.

Fields:

- `required`
- `policy_ref`
- `checkpoint_before_wait`
- `approval_modes`

### `ObservabilityPolicy`

Defines what runtime data should be captured.

Fields:

- `tracing_required`
- `audit_required`
- `capture_prompts`
- `capture_outputs`

### `EvaluationPolicy`

Defines evaluation expectations before deployment.

Fields:

- `required_eval_suite`
- `minimum_score`
- `block_deployment_on_failure`

### `AgentManifest`

The versioned behavior contract for an agent.

Important fields:

- identity: `id`, `name`, `version`
- purpose: `role`, `goal`, `description`
- implementation: `framework`, `model`
- governance: `data_classification`, `policies`, `guardrails`
- dependencies: `skills`, `tools`, `knowledge`, `sub_agents`
- operating policies: `memory`, `execution`, `human_approval`, `observability`, `evaluation`

Method:

- `agent_id_must_be_canonical(value)`: validates that manifest IDs do not contain spaces.

### `AgentDefinition`

The persistent identity of an agent.

Fields:

- `agent_id`
- `tenant_id`
- `name`
- `owner`
- `risk_class`
- `status`
- `created_at`

### `AgentVersion`

A published version of an agent manifest.

Fields:

- `version_id`
- `agent_id`
- `manifest`
- `status`
- `checksum`
- `created_at`

### `AgentRunStatus`

Enum for runtime status: queued, running, waiting for human, completed, failed, cancelled.

### `AgentRun`

One execution attempt.

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

### `PolicyDecision`

Result from policy evaluation.

Fields:

- `decision_id`
- `decision`
- `constraints`
- `reason`

## Learning Point

These classes do not execute agents. They define the nouns and rules that every later layer depends on.
