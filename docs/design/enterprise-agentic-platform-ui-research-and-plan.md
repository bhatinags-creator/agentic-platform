# Enterprise Agentic Platform UI Research and Development Plan

Date: 2026-10-08

## Purpose

This document freezes the research-backed UI architecture for the next development stage. It compares established agentic platforms, assesses the current repository, and defines an incremental plan to evolve the current local Studio into an enterprise-grade low-code/no-code platform.

Primary demonstration use case: **AU Bank Product Advisor**.

## Research Sources

| Platform | Official references used | Verified UX patterns |
| --- | --- | --- |
| Dify | https://www.dify.ai/workflows, https://dify-docs.docs7.io/en/cloud/use-dify/build/workflow-chatflow, https://dify-docs.docs7.io/en/cloud/use-dify/knowledge/knowledge-pipeline/knowledge-pipeline-orchestration | App/workflow split, visual workflow canvas, model calls, knowledge retrieval, tools, code, branching, triggers, human review, app/API/tool publishing, knowledge pipeline with file upload, web crawler, chunking, extraction. |
| Flowise | https://docs.flowiseai.com/, https://github.com/FlowiseAI/Flowise/blob/main/packages/agentflow/README.md | Three builders: Assistant, Chatflow, Agentflow. Visual builder, tracing, analytics, evaluations, HITL, API/CLI/SDK, teams/workspaces, Agentflow nodes for Start, Agent, LLM, Condition, Tool, Retriever, HTTP, Iteration, Execute Flow. |
| Langflow | https://docs.langflow.org/agents, https://docs.langflow.org/concepts-playground | Flow canvas with Agent component, model provider settings, component inspection panel, Tool Mode, MCP tools, memory, Playground with tool calls, raw tool output, streamed events, structured response. |
| Microsoft Copilot Studio | https://learn.microsoft.com/en-us/microsoft-copilot-studio/ | Enterprise agent builder, lifecycle/governance orientation, knowledge/tools/topics, Microsoft ecosystem connectors and governance model. |
| n8n | https://docs.n8n.io/, https://github.com/n8n-io/n8n-docs/blob/main/docs/build/build-and-manage-agents.md | Automation-first workflow canvas, AI Agent node, tools section with built-in integrations, custom JSON schema tools, external MCP servers, web search capabilities, reusable workflows as tools. |
| CrewAI AMP | https://docs.crewai.com/enterprise/introduction | Enterprise Agent Management Platform for deploying, monitoring, and scaling crews and agents; production collaboration and scalability focus. |
| Agno AgentOS | https://docs.agno.com/features/control-plane, https://docs.agno.com/agent-os/overview | Control plane over local/staging/prod runtimes, agents/teams/workflows, run/test/debug, traces, sessions, knowledge, memory, evaluations, approvals, scheduler, runtime endpoint selector. |
| LangSmith Studio | https://docs.langchain.com/langsmith/quick-start-studio | Studio for LangGraph applications, graph mode, streamed execution, state inspection, tracing/evaluation/prompt engineering integration. |

## Competitive Feature Matrix

| Capability | Dify | Flowise | Langflow | Copilot Studio | n8n | CrewAI AMP | Agno AgentOS | LangSmith Studio | Target Platform |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Agent builder | Yes | Yes | Agent component | Yes | AI Agent node | Crew/agent mgmt | Agents/teams/workflows | LangGraph apps | Agent Studio |
| Prompt editor | Yes | Node/config based | Agent instructions | Yes | Node params | Framework config | Component versions | Prompt engineering | Prompt Studio |
| Tool registry | Tools/custom APIs/MCP | Tools/MCP/custom nodes | Tool Mode/MCP | Connectors/actions | Integrations/MCP/custom tools | Crew tools | Registered tools | Code/runtime tools | Tool Studio |
| Visual workflow | Yes | Strong Agentflow canvas | Strong flow canvas | Topics/flows | Strong automation canvas | Crew/flow mgmt | Workflows | Graph mode | Workflow Studio with React Flow |
| Knowledge/RAG | Strong | Document stores/retrievers | Components/vector stores | Knowledge sources | Integrations/vector flows | Framework dependent | Knowledge | App dependent | Knowledge Studio |
| Playground/testing | Yes | Chat/test flows | Playground with tool calls | Test agent | Manual/test runs | Monitoring | Run/test | Studio runner | Agent Testing Studio |
| Tracing/debugging | Monitoring | Tracing/analytics | Playground events | Admin visibility | Execution history | Tracing | Trace trees | Core strength | Observability Center |
| HITL | Human review in workflows | HITL | Can compose | Approvals/governance | HITL patterns | Enterprise ops | Approvals | App dependent | Approval policies + queues |
| Deployment/versioning | App/API/tool publish | API/embed/self-host | Deploy/API | Managed lifecycle | Workflow activation | Deploy/scale | Runtime endpoints | Deployment UI | Deployment Console |
| Enterprise governance | Moderate to strong | RBAC/SSO/teams | Lower enterprise depth | Strong | Projects/creds/RBAC | Enterprise | Strong control plane | Strong tracing/evals | Governance Hub |

## Current Codebase Assessment

### Existing strengths

- Backend is already organized around platform services: `agent_registry`, `agent_studio`, `prompt_management`, `tool_gateway`, `studio_assets`, `runtime_execution`, `rag_platform`, `evaluation_service`, `deployment_service`, `memory_governance`, `finops_service`, `responsible_ai`, `aisecops`, `observability`, `audit_service`, `policy_engine`, and `human_task_service`.
- FastAPI control plane exists in `apps/control_plane_api/main.py`.
- Runtime API exists in `apps/runtime_api/main.py`.
- Domain models in `platform_common/domain/models.py` are framework-neutral and already include manifest references for tools, knowledge, guardrails, policies, sub-agents, memory, execution, approvals, observability, and evaluation.
- Tests are broad: current full suite recently passed with 103 tests.
- Local laptop deployment is feasible through SQLite, Docker assets, and PowerShell scripts.

### Current UI state

- `apps/control_plane_api/studio_ui.py` is a server-rendered HTML/CSS/vanilla JS page.
- It now uses backend APIs for agents, drafts, prompts, tools, rules, and workflows.
- It is useful for local validation but is not yet the target React/TypeScript/Tailwind/React Flow application.

### Gaps against the target platform

| Area | Current state | Gap |
| --- | --- | --- |
| Frontend stack | Server-rendered HTML string | Need React + TypeScript + Tailwind app, componentized design system. |
| Workflow canvas | Linear HTML node list | Need React Flow canvas with typed nodes, edges, validation, state inspection. |
| Prompt Studio | Basic create/list through backend | Need variables, prompt comparison, version publish/rollback, tests. |
| Tool Studio | Basic tool registration | Need REST/OpenAPI import, MCP integration UI, auth config, schemas, test runner. |
| Model configuration | Manifest fields only | Need model provider registry, credentials, routing policy, tenant model access. |
| Knowledge Studio | Backend primitives exist | Need upload/ingestion APIs and UI for chunking, embeddings, retrieval testing. |
| Agent Testing Studio | Service test harness exists | Need chat playground, tool-call timeline, trace viewer, evaluation integration. |
| Governance UI | Services exist | Need tenant/workspace/RBAC screens, approvals, audit, lifecycle gates. |
| Deployment UI | Service exists | Need deployment promotion, environment targets, version history, rollback. |
| Persistence | Mixed in-memory and SQLite | Need persistence for prompt/tool/studio assets beyond runtime process. |

## Recommended Information Architecture

Left navigation:

1. Home
2. Agent Studio
3. Prompt Studio
4. Tool Studio
5. Workflow Studio
6. Knowledge Studio
7. Testing Studio
8. Evaluations
9. Deployments
10. Observability
11. Governance
12. AISecOps
13. FinOps
14. Admin Settings

Global header:

- Tenant selector
- Workspace selector
- Environment selector: local, dev, staging, prod
- Runtime endpoint selector
- Search
- Notifications/approval queue
- Current user and role

Core layout pattern:

- Left product navigation
- Resource list or project explorer
- Main workspace
- Right inspector/configuration panel
- Bottom drawer for logs, traces, validation, and test output

## Key User Journeys

### Agent creation: AU Bank Product Advisor

1. User opens Agent Studio and clicks Create Agent.
2. Enters name: AU Bank Product Advisor.
3. Selects framework: LangGraph.
4. Selects model profile.
5. Defines role/objective and system prompt.
6. Adds official AU Bank search tool from Tool Studio.
7. Attaches product knowledge base from Knowledge Studio.
8. Adds guardrails for financial-advice disclaimers and source citation.
9. Saves draft.
10. Runs validation.
11. Opens Testing Studio and asks product questions.
12. Reviews retrieved evidence and tool calls.
13. Publishes v0.1.0 after evaluation gates pass.

### Tool creation

1. User opens Tool Studio.
2. Chooses REST API Tool or OpenAPI Import.
3. Defines name, description, auth, base URL, operation, input/output schema.
4. Sets permissions: tenant, agent allowlist, actions, risk class.
5. Runs a test invocation.
6. Saves versioned tool definition.
7. Tool becomes attachable in Agent Studio and Workflow Studio.

### Workflow execution

1. User opens Workflow Studio for selected agent.
2. Adds Start, Agent, Knowledge Retrieval, Tool, Condition, Human Approval, and End nodes.
3. Connects nodes on canvas.
4. Configures each node in right inspector.
5. Runs dry-run against sample input.
6. Reviews execution timeline, state diff, tool calls, retrieval evidence, and errors.
7. Saves workflow version.
8. Publishes through deployment gates.

## Screen-by-Screen Design Specifications

### Agent Studio

Primary references: Dify agent creation, Langflow inspector panels, Copilot Studio governance.

Functional requirements:

- Create, edit, clone, validate, publish, deprecate agents.
- Configure basic info, framework, model, role, objective, prompt, variables, tools, skills, knowledge, memory, guardrails, approvals, runtime settings.
- Show readiness checklist tied to backend validation.

Fields:

- name, owner, description, framework, risk class, data classification, version, role, objective, model provider/profile, temperature, max tokens, memory policy, approval policy.

APIs:

- `GET /agents`
- `POST /agents`
- `GET /studio/agent-drafts`
- `POST /studio/agent-drafts`
- `PUT /studio/agent-drafts/{draft_id}`
- `POST /studio/agent-drafts/{draft_id}/validate`
- `POST /studio/agent-drafts/{draft_id}/publish`

States:

- Loading agent list, empty tenant, validation errors, duplicate name, publish blocked by governance gate.

Permissions:

- Builder can create drafts; Reviewer can approve; Admin can publish to production.

### Prompt Studio

Primary references: LangSmith prompt engineering, Dify prompt orchestration.

Functional requirements:

- Template library, system/user/developer instructions, variable editor, version history, prompt test, comparison.

Fields:

- template name, owner, description, version, prompt type, system instruction, user template, developer instruction, variables, tags.

APIs:

- `GET /studio/prompts`
- `POST /studio/prompts`
- Future: `POST /studio/prompts/{template_id}/versions`, `POST /studio/prompts/{version_id}/render`, `POST /studio/prompts/{version_id}/compare`.

### Tool Studio

Primary references: n8n integrations, Langflow Tool Mode/MCP, Flowise tools.

Functional requirements:

- Tool registry, REST tools, OpenAPI import, MCP connections, DB connectors, Python function tools, auth, schemas, testing, permissions.

Fields:

- tool name, type, description, risk class, auth type, endpoint, method, input schema, output schema, timeout, allowed agents, allowed actions.

APIs:

- `GET /studio/tools`
- `POST /studio/tools`
- Future: `POST /studio/tools/import-openapi`, `POST /studio/tools/{tool_id}/test`, `POST /studio/mcp/servers`.

### Workflow Studio

Primary references: Flowise Agentflow, Langflow canvas, n8n workflow canvas, LangSmith graph mode.

Functional requirements:

- React Flow canvas with typed nodes: Start, End, Agent, LLM, Tool, Knowledge Retrieval, Condition, Parallel, Loop, Human Approval, Subworkflow, Error Handler, Agent Delegation.
- Initial runtime target: LangGraph.
- Validate edges, node config, unreachable nodes, missing end nodes, risk approvals.

APIs:

- `GET /studio/workflows?agent_id=...`
- `POST /studio/workflows`
- Future: `POST /studio/workflows/{workflow_id}/validate`, `POST /studio/workflows/{workflow_id}/compile/langgraph`, `POST /runtime/runs`.

### Knowledge Studio

Primary references: Dify Knowledge Pipeline, Flowise document stores/retrievers.

Functional requirements:

- Data source registration, upload, web ingestion, chunking, embeddings, hybrid retrieval, reranking, retrieval testing, citations.

APIs:

- Existing service: `services/rag_platform/service.py`.
- Future control-plane APIs: `POST /knowledge-bases`, `POST /knowledge-bases/{id}/documents`, `POST /knowledge-bases/{id}/retrieve-test`.

### Agent Testing Studio

Primary references: Langflow Playground, LangSmith Studio/tracing.

Functional requirements:

- Chat playground, test inputs, workflow timeline, prompt debugging, tool call inspection, retrieved evidence, quality evaluation, regression datasets.

APIs:

- Existing runtime APIs in `apps/runtime_api/main.py`.
- Future: `POST /runtime/runs`, `GET /runtime/runs/{run_id}`, `GET /observability/traces/{trace_id}`.

### Governance and Observability

Primary references: Agno Control Plane, Copilot Studio governance, LangSmith tracing.

Functional requirements:

- Tenant/workspace admin, RBAC, approval policies, lifecycle gates, version history, audit trail, execution traces, token/cost/latency, guardrail violations, evaluation results.

APIs:

- Build on existing services: auth, policy, audit, observability, finops, evaluation, deployment, human task, AISecOps.

## Component Hierarchy

Recommended frontend package structure:

```text
apps/studio_web/
  src/app/App.tsx
  src/app/routes.tsx
  src/components/layout/Shell.tsx
  src/components/layout/Sidebar.tsx
  src/components/layout/Header.tsx
  src/components/forms/*
  src/features/agents/*
  src/features/prompts/*
  src/features/tools/*
  src/features/workflows/*
  src/features/knowledge/*
  src/features/testing/*
  src/features/governance/*
  src/features/observability/*
  src/lib/api/client.ts
  src/lib/api/types.ts
  src/lib/design-system/*
```

Core reusable components:

- `ResourceList`
- `ResourceHeader`
- `InspectorPanel`
- `ValidationSummary`
- `VersionBadge`
- `PermissionGate`
- `TraceTimeline`
- `EvidenceTable`
- `NodePalette`
- `WorkflowCanvas`
- `NodeInspector`
- `PromptEditor`
- `JsonSchemaEditor`
- `TestRunDrawer`

## Domain Object Schemas

### AgentManifest extension

The existing `AgentManifest` is the correct core. Add UI-specific metadata only under `metadata`, not as top-level framework-specific fields.

Required additions:

- `framework_runtime`: LangGraph, LangChain, CrewAI, custom.
- `model_profile_ref`
- `prompt_refs`
- `workflow_ref`
- `knowledge_refs`
- `guardrail_refs`

### WorkflowDefinition

```json
{
  "workflow_id": "uuid",
  "tenant_id": "tenant-a",
  "agent_id": "uuid",
  "name": "AU Bank Product Advisor Workflow",
  "runtime": "langgraph",
  "nodes": [],
  "edges": [],
  "version": "0.1.0",
  "status": "draft"
}
```

### ToolDefinition

Current service has the right start: tenant, name, risk, allowed agents/actions, timeout. Add auth config, input schema, output schema, implementation type, version, status.

### PromptTemplate

Current service has template/version. Add instruction sections, comparison metadata, variable schema, test cases, publication status.

## API Contract Priorities

Phase 1 APIs:

- `GET /ui/bootstrap`
- `GET /agents`
- `POST /agents`
- `POST /studio/agent-drafts`
- `POST /studio/prompts`
- `GET /studio/prompts`

Phase 2 APIs:

- `GET /model-providers`
- `POST /model-providers`
- `GET /studio/tools`
- `POST /studio/tools`
- `POST /studio/tools/{tool_id}/test`

Phase 3 APIs:

- `GET /studio/workflows`
- `POST /studio/workflows`
- `POST /studio/workflows/{workflow_id}/validate`
- `POST /studio/workflows/{workflow_id}/compile/langgraph`

Phase 4 APIs:

- `POST /knowledge-bases`
- `POST /knowledge-bases/{id}/documents`
- `POST /knowledge-bases/{id}/retrieve-test`
- `POST /runtime/runs`
- `GET /runtime/runs/{run_id}`

Phase 5 APIs:

- `GET /observability/traces`
- `GET /finops/costs`
- `GET /audit/events`
- `GET /approvals`
- `POST /approvals/{id}/decision`
- `POST /deployments`

## Prioritized Roadmap

### Phase 1: Product shell, Agent Studio, Prompt Studio

- Create React/TypeScript/Tailwind app under `apps/studio_web`.
- Add routing and API client.
- Rebuild current backend-backed Agent Studio as React components.
- Add Prompt Studio library and editor.
- Keep current `/studio` HTML page as fallback until React is stable.
- Tests: API tests plus frontend component tests.

### Phase 2: Tool Studio and model configuration

- Add model provider registry and UI.
- Expand Tool Studio with REST tool forms, schema editor, permissions, test runner.
- Add OpenAPI import skeleton and MCP server registry.
- Tests: tool CRUD, permission enforcement, tool test runner.

### Phase 3: Workflow Studio with LangGraph integration

- Add React Flow canvas.
- Add typed node palette and inspector.
- Persist nodes and edges.
- Add LangGraph compiler adapter contract.
- Add dry-run validation.
- Tests: workflow schema validation, compile contract, UI canvas behavior.

### Phase 4: Knowledge Studio and Agent Testing Studio

- Add knowledge base APIs and UI.
- Add document upload/web ingestion skeleton.
- Add retrieval test UI with citation preview.
- Add playground using runtime API.
- Add trace/timeline drawer.
- Tests: RAG registry, retrieval test, runtime trace display.

### Phase 5: Governance, observability, evaluation, deployment

- Add lifecycle gates UI.
- Add approval queue.
- Add deployment targets and rollback UI.
- Add audit, cost, latency, token dashboards.
- Add Responsible AI, AISecOps, evaluation evidence panels.
- Tests: gate enforcement, approval decision, deployment lifecycle.

## Immediate Next Development Steps

1. Commit or checkpoint the current backend-backed HTML Studio changes.
2. Add `apps/studio_web` React/Vite/Tailwind project.
3. Add generated or hand-written TypeScript API types matching `apps/control_plane_api/schemas.py`.
4. Build shell layout and route structure.
5. Implement Agent Studio list/create/draft flow for AU Bank Product Advisor.
6. Implement Prompt Studio create/list flow.
7. Keep all controls either backed by APIs or marked `Coming soon`.

## Design Principle

The target UI should feel like a control plane, not a marketing page. Builders should always know:

- What resource they are editing.
- Which tenant/workspace/environment is active.
- Whether the resource is draft, validated, published, deployed, or blocked.
- Which backend API action will happen when they click a button.
- Which features are ready versus intentionally not implemented yet.
