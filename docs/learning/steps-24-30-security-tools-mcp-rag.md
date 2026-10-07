# Steps 24-30 - Runtime AISecOps, Tool Governance, MCP, and RAG Platform

Date completed: 2026-10-07

## Purpose

These steps connect the runtime to AI security monitoring, introduce governed tool invocation, define MCP adapter contracts, and turn RAG from a stub into a small governed knowledge platform.

## Step 24 - Runtime AISecOps Hooks

File:

- `services/runtime_execution/service.py`

Implemented:

- Runtime prompt attack inspection through `AISecOpsMonitoringService.inspect_prompt(...)`.
- `agent_run.aisecops_signal_recorded` audit event when a prompt signal is found.
- `agent_run.aisecops_checked` audit event for completed runs.
- RAG poisoning signal creation when retrieved chunks contain suspicious terms.
- Tool abuse signal creation when tool invocation governance denies a tool call.
- `aisecops` section in runtime output.

Learning point:

AISecOps should not live only in a dashboard. Runtime must emit security evidence while the agent is actually operating.

## Steps 25-26 - Tool Registry and Tool Invocation Governance

File:

- `services/tool_gateway/service.py`

### `ToolRiskClass`

Enum for tool risk: low, medium, high, critical.

### `ToolStatus`

Enum for tool lifecycle: active, deprecated, disabled.

### `ToolInvocationStatus`

Enum for invocation result: succeeded, denied, failed.

### `ToolDefinition`

Governed tool record.

Fields include tenant, name, description, risk class, allowed agents, allowed actions, timeout, status, and creation time.

### `ToolInvocationDecision`

Policy-style decision object describing whether the invocation is permitted and why.

### `ToolInvocationRecord`

Evidence record for each attempted tool invocation.

### `ToolRegistryService`

Methods:

- `register_tool(...)`: registers a governed tool.
- `get_tool(...)`: loads tenant or default tool by name.
- `list_tools(...)`: lists tenant-visible tools.
- `deprecate_tool(...)`: marks a tool deprecated.

### `ToolGatewayService`

Methods:

- `invoke(...)`: checks registry and policy before executing a mock tool.
- `evaluate_invocation(...)`: enforces status, allowed agents, and allowed actions.
- `list_invocations(...)`: returns tenant-scoped invocation evidence.
- `_record_invocation(...)`: stores invocation record.
- `_ensure_default_tools(...)`: registers `mvp.echo` for runtime compatibility.

## Step 27 - MCP Adapter Foundation

File:

- `protocols/mcp/service.py`

### `MCPServerStatus`

Enum for MCP server lifecycle.

### `MCPServerDefinition`

Registered MCP server metadata.

### `MCPToolReference`

Tool reference discovered from an MCP server.

### `MCPResourceReference`

Resource reference discovered from an MCP server.

### `MCPAdapter`

Protocol defining the adapter boundary for listing tools and resources.

### `StaticMCPAdapter`

Test-friendly adapter that returns preconfigured tools and resources.

### `MCPAdapterRegistry`

Methods:

- `register_server(...)`: registers an MCP server.
- `get_server(...)`: tenant-scoped lookup.
- `list_servers(...)`: tenant-scoped server listing.
- `list_server_tools(...)`: lists tools through the adapter.
- `list_server_resources(...)`: lists resources through the adapter.

## Steps 28-30 - Knowledge Base Registry, Ingestion, and Retrieval Governance

File:

- `services/rag_platform/service.py`

### `KnowledgeBaseStatus`

Enum for knowledge base lifecycle.

### `IngestionJobStatus`

Enum for ingestion outcome.

### `RetrievalSafetyStatus`

Enum for retrieval governance outcome: passed or review required.

### `KnowledgeBase`

Tenant-scoped knowledge source registry record.

### `KnowledgeDocument`

Document stored inside a knowledge base.

### `DocumentChunk`

Chunk created from a document during ingestion.

### `IngestionJob`

Evidence record for document ingestion.

### `Citation`

Source citation attached to retrieval results.

### `RetrievalResult`

Governed retrieval result containing text, score, citation, safety status, and safety findings.

### `RetrievalGovernanceReport`

Aggregate report over retrieval results.

### `RAGPlatformService`

Methods:

- `create_knowledge_base(...)`: registers a tenant knowledge base.
- `get_knowledge_base(...)`: tenant-scoped lookup.
- `list_knowledge_bases(...)`: lists tenant knowledge bases.
- `ingest_document(...)`: stores a document and chunks it.
- `retrieve(...)`: async runtime retrieval path with default fallback.
- `search(...)`: tenant-scoped retrieval search.
- `govern_retrievals(...)`: checks citations and safety findings.
- `list_ingestion_jobs(...)`: lists ingestion jobs.
- `_chunk_document(...)`: simple local chunker.
- `_chunk_to_result(...)`: creates governed retrieval result.
- `_result_to_runtime_dict(...)`: converts retrieval model to runtime output shape.
- `_ensure_default_content(...)`: preserves the MVP runtime path.

## Tests

Added or updated:

- `tests/test_tool_gateway.py`
- `tests/test_mcp_adapter.py`
- `tests/test_rag_platform.py`
- `tests/test_runtime_execution.py`
- `tests/test_runtime_persistence.py`

## Verification

```text
python -m ruff check .
All checks passed!

python -m pytest
76 passed, 1 warning
```

## Learning Summary

This batch adds three major enterprise platform ideas:

1. Agent security monitoring must be runtime-aware.
2. Tools are privileged capabilities, so they need registry, policy, and evidence.
3. RAG is not just retrieval; it needs source registry, ingestion evidence, citations, and safety checks.

The platform now has this governed runtime path:

```text
Policy -> AISecOps Prompt Check -> RAG Retrieval Governance -> Tool Governance -> Model -> FinOps -> Responsible AI -> Memory -> Audit
```
