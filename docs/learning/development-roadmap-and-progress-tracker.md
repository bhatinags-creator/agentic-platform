# Agentic Platform Development Roadmap and Progress Tracker

Last updated: 2026-10-06

## Current Status

We have completed Steps 01 to 30.

Current platform stage:

```text
Foundation + Control Plane MVP + Runtime Plane MVP + Governance Hooks + Persistent Runtime Stores + Agent Studio Foundations + Evaluation + Responsible AI + AISecOps + Tool Governance + MCP + RAG Platform
```

The platform can currently:

- define enterprise agent contracts
- register agents and publish versions
- persist registry data locally in SQLite
- expose Control Plane APIs
- start Runtime Plane agent runs
- call mock RAG, Tool Gateway, and Model Gateway services
- apply runtime policy decisions
- write audit events
- record AI FinOps cost events
- record governed memory records with retention metadata
- persist runtime runs, audit events, cost events, and memory records locally in SQLite
- create Agent Studio drafts
- validate and publish Agent Studio drafts into the registry
- manage versioned prompt templates
- run an Agent Studio test harness
- create evaluation suites and cases
- run offline, online, LLM-as-judge, and safety evaluation flows
- capture Responsible AI fairness, bias, explainability, model risk, and regulatory evidence
- attach Responsible AI runtime assessments to completed agent runs
- record AISecOps security monitoring signals for prompt attacks, agent behavior, RAG poisoning, model drift, tool abuse, and anomalies
- run AISecOps checks inside runtime execution
- register and govern tool invocation
- register MCP servers and list MCP tools/resources
- register knowledge bases, ingest documents, create chunks, attach citations, and govern retrieval safety

Current verification baseline:

```text
python -m ruff check .
All checks passed!

python -m pytest
58 passed, 1 warning
```

## How to Use This Plan

Use this document as the master checklist.

Each step should ideally produce:

- code implementation
- unit tests or API tests
- learning markdown
- passing Ruff
- passing pytest

Progress labels:

- Done: implemented and tested
- Next: recommended next development step
- Planned: not started
- Later: advanced/production hardening

## Phase 1 - Platform Foundation

### Step 01 - Platform Contracts

Status: Done

Purpose: Create the shared domain language for the platform.

Key files:

- `platform_common/domain/models.py`
- `platform_common/events/envelope.py`
- `docs/learning/step-01-platform-contracts.md`

## Phase 2 - Agent Registry and Control Plane

### Step 02 - Agent Registry Service

Status: Done

Purpose: Create the service that owns agent registration and version publishing rules.

Key files:

- `services/agent_registry/service.py`
- `tests/test_agent_registry.py`
- `docs/learning/step-02-persistent-agent-registry.md`

### Step 03 - Control Plane API

Status: Done

Purpose: Expose Agent Registry features through HTTP APIs.

Key files:

- `apps/control_plane_api/main.py`
- `apps/control_plane_api/schemas.py`
- `tests/test_control_plane_api.py`
- `docs/learning/step-03-control-plane-api.md`

### Step 04 - SQLite Agent Registry Persistence

Status: Done

Purpose: Make local laptop registry data durable across API restarts.

Key files:

- `services/agent_registry/sqlite_repository.py`
- `.env.example`
- `tests/test_sqlite_agent_registry_repository.py`
- `docs/learning/step-04-sqlite-agent-registry-persistence.md`

## Phase 3 - Runtime Plane MVP

### Step 05 - Runtime Plane Execution Path

Status: Done

Purpose: Create the first runtime execution path for agent runs.

Key files:

- `services/runtime_execution/service.py`
- `apps/runtime_api/main.py`
- `apps/runtime_api/schemas.py`
- `tests/test_runtime_execution.py`
- `tests/test_runtime_api.py`
- `docs/learning/step-05-runtime-plane-execution-path.md`

## Phase 4 - Runtime Governance Hooks

### Step 06 - Runtime Policy Gate and Audit Trail

Status: Done

Purpose: Add enterprise control and evidence to runtime execution.

Key files:

- `services/policy_engine/service.py`
- `services/audit_service/service.py`
- `services/runtime_execution/service.py`
- `docs/learning/step-06-runtime-policy-and-audit.md`

### Step 07 - AI FinOps Cost Governance

Status: Done

Purpose: Track AI model usage and cost at runtime.

Key files:

- `services/finops_service/service.py`
- `services/runtime_execution/service.py`
- `tests/test_finops_service.py`
- `docs/learning/step-07-ai-finops-cost-governance.md`

### Step 08 - Memory Governance Runtime Integration

Status: Done

Purpose: Classify runtime memory and attach retention metadata.

Key files:

- `services/memory_governance/service.py`
- `services/runtime_execution/service.py`
- `tests/test_memory_governance.py`
- `docs/learning/step-08-memory-governance-runtime-integration.md`

## Phase 5 - Runtime Persistence and Operational APIs

### Step 09 - Persistent Runtime Run Store

Status: Done

Purpose: Persist runtime runs beyond process memory.

Key files:

- `services/runtime_execution/sqlite_repository.py`
- `tests/test_runtime_persistence.py`
- `docs/learning/steps-09-12-runtime-persistence.md`

### Step 10 - Persistent Audit Store

Status: Done

Purpose: Persist audit records instead of keeping them in memory.

Key files:

- `services/audit_service/service.py`
- `tests/test_runtime_persistence.py`
- `docs/learning/steps-09-12-runtime-persistence.md`

### Step 11 - Persistent FinOps Store

Status: Done

Purpose: Persist cost events for reporting and budget tracking.

Key files:

- `services/finops_service/service.py`
- `tests/test_runtime_persistence.py`
- `docs/learning/steps-09-12-runtime-persistence.md`

### Step 12 - Persistent Memory Store

Status: Done

Purpose: Persist governed memory records and support retention cleanup.

Key files:

- `services/memory_governance/service.py`
- `tests/test_runtime_persistence.py`
- `docs/learning/steps-09-12-runtime-persistence.md`

## Phase 6 - Agent Studio Foundations

### Step 13 - Agent Studio Backend API

Status: Done

Purpose: Create APIs that Agent Studio UI will use.

Key files:

- `services/agent_studio/service.py`
- `apps/control_plane_api/main.py`
- `apps/control_plane_api/schemas.py`
- `tests/test_agent_studio.py`
- `tests/test_agent_studio_api.py`
- `docs/learning/step-13-agent-studio-backend-api.md`

### Step 14 - Prompt and Template Management

Status: Done

Purpose: Manage prompts as governed, versioned assets.

Implemented:

- prompt template lifecycle model
- prompt version model
- variable extraction
- prompt rendering validation
- tenant-scoped lookup

Key files:

- `services/prompt_management/service.py`
- `tests/test_prompt_management.py`
- `docs/learning/steps-14-22-studio-evaluation-responsible-ai.md`

### Step 15 - Agent Test Harness

Status: Done

Purpose: Allow users to test Agent Studio drafts before publishing and deployment.

Implemented:

- `AgentTestCase`
- `AgentTestRunResult`
- validation-aware draft test runs
- deterministic simulated output checks

Key files:

- `services/agent_studio/service.py`
- `tests/test_agent_studio.py`
- `docs/learning/steps-14-22-studio-evaluation-responsible-ai.md`

## Phase 7 - Evaluation Architecture

### Step 16 - Evaluation Domain Models

Status: Done

Purpose: Define evaluation suites, cases, results, and scoring contracts.

### Step 17 - Offline Evaluation

Status: Done

Purpose: Run golden dataset and prompt regression style tests.

### Step 18 - Online Evaluation

Status: Done

Purpose: Collect user feedback and human scoring.

### Step 19 - LLM-as-Judge Evaluation

Status: Done

Purpose: Add automated quality scoring contracts.

### Step 20 - Safety Evaluation

Status: Done

Purpose: Evaluate hallucination, groundedness, toxicity, PII leakage, and prompt injection resilience.

Key files for Steps 16-20:

- `services/evaluation_service/service.py`
- `tests/test_evaluation_service.py`
- `docs/learning/steps-14-22-studio-evaluation-responsible-ai.md`

## Phase 8 - Responsible AI

### Step 21 - Responsible AI Service

Status: Done

Purpose: Track fairness, bias, explainability, model risk, and regulatory evidence.

Implemented:

- fairness test records
- bias detection results
- explainability reports
- model risk records
- regulatory evidence records

Key files:

- `services/responsible_ai/service.py`
- `tests/test_responsible_ai_service.py`
- `docs/learning/steps-14-22-studio-evaluation-responsible-ai.md`

### Step 22 - Responsible AI Runtime Hooks

Status: Done

Purpose: Connect Responsible AI checks to runtime evidence capture.

Implemented:

- runtime Responsible AI assessment
- `responsible_ai` run output section
- `agent_run.responsible_ai_checked` audit event

Key files:

- `services/runtime_execution/service.py`
- `tests/test_runtime_execution.py`
- `tests/test_runtime_persistence.py`
- `docs/learning/steps-14-22-studio-evaluation-responsible-ai.md`

## Phase 9 - AISecOps

### Step 23 - AISecOps Monitoring Models

Status: Done

Purpose: Define security monitoring records for AI-specific threats.

Implemented:

- prompt attack monitoring records
- agent behavior monitoring records
- RAG poisoning monitoring records
- model drift monitoring records
- tool abuse monitoring records
- anomaly detection records
- tenant-scoped signal filtering
- signal status lifecycle
- tenant AISecOps summary

Key files:

- `services/aisecops/service.py`
- `tests/test_aisecops_service.py`
- `docs/learning/step-23-aisecops-monitoring-models.md`

### Step 24 - Runtime AISecOps Hooks

Status: Done

Purpose: Detect suspicious runtime behavior.

Implemented:

- runtime prompt attack inspection
- AISecOps audit events
- RAG poisoning signal hook
- tool abuse signal hook
- runtime `aisecops` output section

Key files:

- `services/runtime_execution/service.py`
- `tests/test_runtime_execution.py`
- `docs/learning/steps-24-30-security-tools-mcp-rag.md`

## Phase 10 - Tool Gateway and MCP

### Step 25 - Tool Registry

Status: Done

Purpose: Register and govern tools available to agents.

### Step 26 - Tool Invocation Governance

Status: Done

Purpose: Control which tools agents can call.

### Step 27 - MCP Adapter Foundation

Status: Done

Purpose: Support Model Context Protocol style tool/resource adapters.

## Phase 11 - RAG Platform

### Step 28 - Knowledge Base Registry

Status: Done

Purpose: Register governed knowledge sources.

### Step 29 - Ingestion Pipeline MVP

Status: Done

Purpose: Load and chunk documents for retrieval.

### Step 30 - Retrieval Governance

Status: Done

Purpose: Track citations, source permissions, and RAG safety.

## Phase 12 - Deployment Architecture

### Step 31 - Deployment Service MVP

Status: Next

Purpose: Deploy published agent versions into runtime environments.

### Step 32 - Deployment Gates

Status: Planned

Purpose: Block deployment unless policy, evaluation, Responsible AI, and security checks pass.

### Step 33 - Local Laptop Deployment Scripts

Status: Planned

Purpose: Make local startup easy.

## Phase 13 - Human-in-the-Loop

### Step 34 - Human Task Service MVP

Status: Planned

Purpose: Create and track human approvals.

### Step 35 - Runtime Human Approval Checkpoints

Status: Planned

Purpose: Pause runs when policy requires human approval.

## Phase 14 - Observability

### Step 36 - Trace and Span Model

Status: Planned

Purpose: Standardize traces across runtime calls.

### Step 37 - Metrics API

Status: Planned

Purpose: Expose operational metrics.

## Phase 15 - SDK and Developer Experience

### Step 38 - Python SDK Expansion

Status: Planned

Purpose: Make the platform easy to use from Python code.

### Step 39 - CLI Tool

Status: Planned

Purpose: Manage the platform from terminal.

## Phase 16 - UI and Agent Studio

### Step 40 - Minimal Local Agent Studio UI

Status: Planned

Purpose: Provide a browser UI for local usage.

### Step 41 - Evaluation Workspace UI

Status: Planned

Purpose: View and run evaluations.

### Step 42 - Deployment Console UI

Status: Planned

Purpose: Deploy and manage agent versions.

## Phase 17 - Production Hardening

### Step 43 - Authentication and Authorization

Status: Later

Purpose: Protect APIs with real auth.

### Step 44 - Postgres Migration

Status: Later

Purpose: Move from SQLite to enterprise database.

### Step 45 - Event Bus Integration

Status: Later

Purpose: Publish platform events asynchronously.

### Step 46 - Background Workers

Status: Later

Purpose: Run async jobs outside API request lifecycle.

### Step 47 - Containerization and Kubernetes

Status: Later

Purpose: Prepare services for production deployment.

### Step 48 - Security Hardening

Status: Later

Purpose: Harden platform security posture.

## Suggested Next 10 Steps

Recommended immediate sequence from our current point:

1. Step 31 - Deployment Service MVP
2. Step 32 - Deployment Gates
3. Step 33 - Local Laptop Deployment Scripts
4. Step 34 - Human Task Service MVP
5. Step 35 - Runtime Human Approval Checkpoints
6. Step 36 - Trace and Span Model
7. Step 37 - Metrics API
8. Step 38 - Python SDK Expansion
9. Step 39 - CLI Tool
10. Step 40 - Minimal Local Agent Studio UI

## Progress Summary

Completed:

- Step 01 - Platform Contracts
- Step 02 - Agent Registry Service
- Step 03 - Control Plane API
- Step 04 - SQLite Agent Registry Persistence
- Step 05 - Runtime Plane Execution Path
- Step 06 - Runtime Policy Gate and Audit Trail
- Step 07 - AI FinOps Cost Governance
- Step 08 - Memory Governance Runtime Integration
- Step 09 - Persistent Runtime Run Store
- Step 10 - Persistent Audit Store
- Step 11 - Persistent FinOps Store
- Step 12 - Persistent Memory Store
- Step 13 - Agent Studio Backend API
- Step 14 - Prompt and Template Management
- Step 15 - Agent Test Harness
- Step 16 - Evaluation Domain Models
- Step 17 - Offline Evaluation
- Step 18 - Online Evaluation
- Step 19 - LLM-as-Judge Evaluation
- Step 20 - Safety Evaluation
- Step 21 - Responsible AI Service
- Step 22 - Responsible AI Runtime Hooks
- Step 23 - AISecOps Monitoring Models
- Step 24 - Runtime AISecOps Hooks
- Step 25 - Tool Registry
- Step 26 - Tool Invocation Governance
- Step 27 - MCP Adapter Foundation
- Step 28 - Knowledge Base Registry
- Step 29 - Ingestion Pipeline MVP
- Step 30 - Retrieval Governance

Next:

- Step 31 - Deployment Service MVP

Total roadmap steps listed:

```text
48
```

Completed:

```text
30 / 48
```

Approximate completion:

```text
62.5%
```

Note: the percentage is based on planned development steps, not calendar effort. Some later steps are larger than early ones.



