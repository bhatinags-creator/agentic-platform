# Enterprise Agentic AI Platform

Initial MVP scaffold for a framework-neutral enterprise Agentic AI Platform.

## Quick Start

```powershell
cd E:\AIProjects\agentic-platform
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
pytest
uvicorn apps.control_plane_api.main:app --reload --port 8001
uvicorn apps.runtime_api.main:app --reload --port 8002
```

## Design Documents

Frozen design documents are in `docs/design`.

## Architecture Rule

Frameworks are adapters. Platform-owned services control identity, policy, model access, tools, RAG, memory governance, audit, observability, FinOps, Responsible AI, AISecOps, evaluation, and deployment.
