# Phase 1 React Studio

Date: 2026-10-08

## What Phase 1 Adds

Phase 1 introduces a dedicated React/TypeScript frontend under `apps/studio_web`.

It does not replace the FastAPI backend. Instead, it becomes the modern UI layer that talks to the existing control-plane APIs.

## Implemented Screens

### Agent Studio

Purpose: create, validate, and publish agent drafts.

Backend APIs used:

- `GET /agents`
- `POST /agents`
- `GET /studio/agent-drafts`
- `POST /studio/agent-drafts`
- `POST /studio/agent-drafts/{draft_id}/validate`
- `POST /studio/agent-drafts/{draft_id}/publish`

Concepts shown:

- Agent registry record
- Agent draft manifest
- Framework-neutral configuration
- LangGraph/LangChain framework selection
- Model profile fields
- Risk and data classification
- Readiness checks

### Prompt Studio

Purpose: create reusable prompt templates and versions.

Backend APIs used:

- `GET /studio/prompts`
- `POST /studio/prompts`

Concepts shown:

- Prompt template metadata
- Prompt version text
- Owner and description
- Variable detection using `{{ variable_name }}` syntax
- Prompt library list

## UI Shell

The shell contains:

- Left navigation
- Tenant input
- Optional API key input
- Refresh action
- Explicit disabled modules marked as `Soon`

This is intentional. Features that do not yet have working APIs are visible in the roadmap but not disguised as functional controls.

## Key Files

- `apps/studio_web/package.json`: frontend scripts and dependencies.
- `apps/studio_web/vite.config.ts`: Vite app and proxy to the FastAPI backend on port 8001.
- `apps/studio_web/src/lib/api.ts`: typed API client.
- `apps/studio_web/src/types.ts`: frontend domain contracts.
- `apps/studio_web/src/app/App.tsx`: app state and routing.
- `apps/studio_web/src/components/layout/Shell.tsx`: product shell.
- `apps/studio_web/src/components/ui/Primitives.tsx`: reusable UI primitives.
- `apps/studio_web/src/features/agents/AgentStudio.tsx`: Agent Studio screen.
- `apps/studio_web/src/features/prompts/PromptStudio.tsx`: Prompt Studio screen.

## How To Run

Start backend:

```powershell
python -m uvicorn apps.control_plane_api.main:app --host 127.0.0.1 --port 8001
```

Start React frontend:

```powershell
cd E:\AIProjects\agentic-platform\apps\studio_web
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

## Verification

Frontend build:

```powershell
cd E:\AIProjects\agentic-platform\apps\studio_web
npm run build
```

Backend lint check:

```powershell
python -m ruff check apps\control_plane_api services\studio_assets services\prompt_management tests\test_control_plane_api.py
```

## Next Phase

Phase 2 has started in `docs/learning/phase-2-tool-studio-and-model-config.md` and adds:

- Tool Studio
- Model provider configuration
- Tool testing endpoint
- Tool authentication fields
- Input/output schema editor
