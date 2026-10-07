# Step 23 - AISecOps Monitoring Models

Date completed: 2026-10-07

## Purpose

AISecOps is the security operations layer for agentic AI systems. Traditional application security watches APIs, identities, networks, and infrastructure. AISecOps watches AI-specific failure and attack patterns: prompt attacks, strange agent behavior, RAG poisoning, model drift, tool abuse, and runtime anomalies.

This step defines the monitoring records. Step 24 will wire these records into runtime execution.

## File

- `services/aisecops/service.py`

## Core Concepts

### Prompt Attack Monitoring

Detects attempts to override or bypass instructions, extract hidden prompts, or force unsafe behavior.

Example signals:

- `ignore instructions`
- `ignore previous`
- `jailbreak`
- `exfiltrate`
- `reveal system prompt`

### Agent Behavior Monitoring

Captures suspicious agent behavior, such as unexpected recursive planning, tool loops, repeated failures, or policy-avoidant behavior.

### RAG Poisoning Monitoring

Captures suspicious retrieval or knowledge-base signals, such as poisoned documents, malicious source text, or retrieval content that tries to manipulate the agent.

### Model Drift Detection

Captures model-output drift against an expected baseline. In this MVP it stores a deterministic `drift_score`; later this can come from evaluation metrics or statistical monitors.

### Tool Abuse Detection

Captures suspicious tool use, such as repeated export attempts, destructive actions, unusual parameter values, or unauthorized tool patterns.

### Anomaly Detection

Captures general abnormal behavior using an `anomaly_score` and evidence payload.

## Classes

### `AISecOpsSignalType`

Enum for AI security signal categories.

Values:

- `PROMPT_ATTACK`
- `AGENT_BEHAVIOR`
- `RAG_POISONING`
- `MODEL_DRIFT`
- `TOOL_ABUSE`
- `ANOMALY`

### `AISecOpsSeverity`

Enum for severity classification.

Values:

- `NONE`
- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

### `AISecOpsStatus`

Enum for security investigation lifecycle.

Values:

- `OPEN`
- `INVESTIGATING`
- `MITIGATED`
- `FALSE_POSITIVE`

### `AISecOpsSignal`

Base security signal record.

Important fields:

- `signal_id`: unique signal identifier.
- `tenant_id`: tenant boundary.
- `agent_id`: related agent.
- `signal_type`: category of signal.
- `severity`: severity level.
- `description`: human-readable description.
- `evidence`: structured evidence payload.
- `run_id`: optional runtime run reference.
- `trace_id`: optional trace reference.
- `status`: investigation status.
- `created_at`: timestamp.

### Specialized Records

These extend `AISecOpsSignal` with category-specific fields:

- `PromptAttackMonitoringRecord`: adds `attack_terms`.
- `AgentBehaviorMonitoringRecord`: adds `behavior`.
- `RAGPoisoningMonitoringRecord`: adds `knowledge_source`.
- `ModelDriftMonitoringRecord`: adds `drift_score`.
- `ToolAbuseMonitoringRecord`: adds `tool_name`.
- `AnomalyDetectionRecord`: adds `anomaly_score`.

### `AISecOpsSummary`

Aggregates tenant security signal counts.

Fields:

- `tenant_id`
- `total_signals`
- `open_signals`
- `critical_signals`
- `high_signals`
- `by_type`

### `AISecOpsSignalNotFoundError`

Raised when a caller tries to update a signal that does not exist or belongs to another tenant.

### `AISecOpsMonitoringService`

Owns AISecOps signal creation, filtering, status changes, and summary reporting.

Methods:

- `__init__()`: creates an in-memory signal store.
- `inspect_prompt(...)`: scans prompt text for attack phrases and records a prompt attack signal when matched.
- `record_prompt_attack(...)`: records a prompt attack signal.
- `record_agent_behavior(...)`: records suspicious agent behavior.
- `record_rag_poisoning(...)`: records suspected poisoned retrieval or knowledge source content.
- `record_model_drift(...)`: records model drift with a score and baseline reference.
- `record_tool_abuse(...)`: records suspicious tool usage.
- `record_anomaly(...)`: records a general runtime anomaly.
- `list_signals(...)`: lists tenant-scoped signals with optional filters.
- `update_signal_status(...)`: changes investigation status for a tenant-scoped signal.
- `summarize_tenant(...)`: returns signal counts by severity and type.
- `_save(...)`: stores a signal.
- `_severity_from_score(...)`: maps drift/anomaly scores to severity.
- `_parse_uuid(...)`: normalizes UUID input.

## Tests

File:

- `tests/test_aisecops_service.py`

Covered behavior:

- prompt attack inspection creates a high-severity signal
- clean prompts do not create signals
- every AISecOps monitoring category can be recorded
- tenant summaries count signals by type and severity
- list filtering works by type, severity, and status
- signal status updates are tenant scoped

## Verification

```text
python -m ruff check .
All checks passed!

python -m pytest
67 passed, 1 warning
```

## Learning Summary

Step 23 does not yet block or change runtime behavior. It creates the security vocabulary and record shape that Step 24 will use.

The new AISecOps lifecycle is:

```text
Detect -> Record Signal -> Investigate -> Mitigate or Mark False Positive
```
