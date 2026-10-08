from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse

from apps.control_plane_api.schemas import (
    AgentDraftListResponse,
    AgentDraftResponse,
    AgentDraftValidationResponse,
    AgentListResponse,
    AgentResponse,
    AgentVersionListResponse,
    AgentVersionResponse,
    CreateAgentDraftRequest,
    CreateAgentRequest,
    PublishAgentVersionRequest,
    UpdateAgentDraftRequest,
)
from services.agent_registry.service import (
    AgentNotFoundError,
    AgentRegistryService,
    DuplicateAgentNameError,
    DuplicateAgentVersionError,
)
from services.agent_registry.sqlite_repository import SQLiteAgentRegistryRepository
from services.agent_studio.service import (
    AgentDraftAlreadyPublishedError,
    AgentDraftNotFoundError,
    AgentStudioService,
)

TenantIdHeader = Annotated[str, Header(alias="X-Tenant-ID")]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "agentic_platform.db"


def build_default_registry() -> AgentRegistryService:
    database_path = Path(os.getenv("AGENTIC_PLATFORM_DB_PATH", str(DEFAULT_DATABASE_PATH)))
    return AgentRegistryService(repository=SQLiteAgentRegistryRepository(database_path))


def create_app(
    registry: AgentRegistryService | None = None,
    studio: AgentStudioService | None = None,
) -> FastAPI:
    app = FastAPI(title="Agentic Platform Control Plane API", version="0.1.0")
    app.state.registry = registry or build_default_registry()
    app.state.studio = studio or AgentStudioService(registry=app.state.registry)
    _configure_optional_api_key_auth(app)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "control-plane-api"}

    @app.get("/studio/evaluations", response_class=HTMLResponse)
    def evaluation_workspace() -> str:
        return """
<!doctype html><html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Evaluation Workspace</title><style>
body{margin:0;background:#f7f8fa;color:#20242c;font-family:Inter,Segoe UI,Arial,sans-serif}header{background:#fff;border-bottom:1px solid #d9dee7;padding:14px 22px}h1{font-size:20px;margin:0}.wrap{padding:20px 22px;display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}section{background:#fff;border:1px solid #d9dee7;border-radius:8px;padding:16px}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:8px;border-bottom:1px solid #eef1f5}button,input{height:34px;border:1px solid #b9c1ce;border-radius:6px;padding:0 10px}button{background:#27364a;color:white}</style></head>
<body><header><h1>Evaluation Workspace</h1></header><div class="wrap"><section><h2>Suites</h2><table><thead><tr><th>Name</th><th>Mode</th><th>Status</th></tr></thead><tbody><tr><td>Golden Dataset Smoke</td><td>offline</td><td>ready</td></tr><tr><td>Safety Regression</td><td>safety</td><td>ready</td></tr></tbody></table></section><section><h2>Run Evaluation</h2><p>Use the service layer to create suites and run offline, online, judge, and safety evaluations. The production UI will bind these controls to evaluation APIs.</p><button>Run Selected Suite</button></section></div></body></html>
        """

    @app.get("/studio/deployments", response_class=HTMLResponse)
    def deployment_console() -> str:
        return """
<!doctype html><html lang="en"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Deployment Console</title><style>
body{margin:0;background:#f7f8fa;color:#20242c;font-family:Inter,Segoe UI,Arial,sans-serif}header{background:#fff;border-bottom:1px solid #d9dee7;padding:14px 22px}h1{font-size:20px;margin:0}.wrap{padding:20px 22px;display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}section{background:#fff;border:1px solid #d9dee7;border-radius:8px;padding:16px}table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:8px;border-bottom:1px solid #eef1f5}.pass{color:#1f7a4d}.wait{color:#8a5a00}</style></head>
<body><header><h1>Deployment Console</h1></header><div class="wrap"><section><h2>Deployment Gates</h2><table><thead><tr><th>Gate</th><th>Status</th></tr></thead><tbody><tr><td>Policy</td><td class="pass">passed</td></tr><tr><td>Evaluation</td><td class="wait">pending</td></tr><tr><td>Responsible AI</td><td class="pass">passed</td></tr><tr><td>AISecOps</td><td class="pass">passed</td></tr></tbody></table></section><section><h2>Actions</h2><p>Deploy and rollback operations are available in the deployment service. The production console will bind these actions to deployment APIs.</p></section></div></body></html>
        """

    @app.get("/studio", response_class=HTMLResponse)
    def local_agent_studio() -> str:
        return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Agent Studio</title>
  <style>
    :root { color-scheme: light; font-family: Inter, Segoe UI, Arial, sans-serif; }
    body { margin: 0; background: #f7f8fa; color: #20242c; }
    header { background: #ffffff; border-bottom: 1px solid #d9dee7; padding: 14px 22px; display: flex; align-items: center; gap: 16px; }
    h1 { font-size: 20px; margin: 0; font-weight: 650; }
    nav { margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; }
    nav a { color: #27364a; text-decoration: none; border: 1px solid #c8d0dc; border-radius: 6px; padding: 8px 10px; font-size: 13px; background: #ffffff; }
    main { padding: 20px 22px; display: grid; gap: 18px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
    section { background: #ffffff; border: 1px solid #d9dee7; border-radius: 8px; padding: 16px; min-height: 220px; }
    .wide { grid-column: 1 / -1; min-height: 0; }
    .tiles { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }
    .tile { border: 1px solid #d9dee7; border-radius: 8px; padding: 14px; background: #fbfcfe; }
    .tile h3 { margin: 0 0 8px; font-size: 14px; }
    .tile p { margin: 0 0 12px; color: #5b6472; font-size: 13px; line-height: 1.4; }
    .tile a { display: inline-block; color: #ffffff; background: #27364a; border-radius: 6px; padding: 8px 10px; font-size: 13px; text-decoration: none; }
    h2 { font-size: 15px; margin: 0 0 12px; }
    label { font-size: 12px; color: #555f70; display: block; margin-bottom: 4px; }
    input { height: 34px; border: 1px solid #b9c1ce; border-radius: 6px; padding: 0 10px; min-width: 220px; }
    button { height: 36px; border: 1px solid #27364a; border-radius: 6px; background: #27364a; color: white; padding: 0 12px; cursor: pointer; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #eef1f5; vertical-align: top; }
    th { color: #5d6675; font-weight: 600; }
    .toolbar { display: flex; gap: 10px; align-items: end; flex-wrap: wrap; }
    .empty { color: #6b7280; font-size: 13px; }
  </style>
</head>
<body>
  <header>
    <h1>Agent Studio</h1>
    <nav>
      <a href="/studio">Studio Home</a>
      <a href="/studio/evaluations">Evaluation Workspace</a>
      <a href="/studio/deployments">Deployment Console</a>
    </nav>
    <div class="toolbar">
      <div><label for="tenant">Tenant</label><input id="tenant" value="tenant-a" /></div>
      <div><label for="apiKey">API Key</label><input id="apiKey" type="password" placeholder="optional" /></div>
      <button onclick="loadAll()">Refresh</button>
    </div>
  </header>
  <main>
    <section class="wide">
      <h2>Step 41-48 Production Surfaces</h2>
      <div class="tiles">
        <div class="tile"><h3>Evaluation Workspace</h3><p>Run offline, online, judge, and safety evaluation workflows from the new evaluation surface.</p><a href="/studio/evaluations">Open evaluations</a></div>
        <div class="tile"><h3>Deployment Console</h3><p>Inspect deployment gates for policy, evaluation, Responsible AI, and AISecOps readiness.</p><a href="/studio/deployments">Open deployments</a></div>
        <div class="tile"><h3>Production Hardening</h3><p>Steps 43-48 added optional API key auth, Postgres planning, events, workers, Kubernetes hardening, and security checks.</p><a href="/docs">Open API docs</a></div>
      </div>
    </section>
    <section><h2>Agents</h2><div id="agents" class="empty">No data loaded.</div></section>
    <section><h2>Drafts</h2><div id="drafts" class="empty">No data loaded.</div></section>
  </main>
  <script>
    function headers() {
      const requestHeaders = { 'X-Tenant-ID': document.getElementById('tenant').value };
      const apiKey = document.getElementById('apiKey').value;
      if (apiKey) requestHeaders['X-API-Key'] = apiKey;
      return requestHeaders;
    }
    function table(rows, columns) {
      if (!rows.length) return '<p class="empty">Nothing found.</p>';
      return '<table><thead><tr>' + columns.map(c => '<th>' + c.label + '</th>').join('') + '</tr></thead><tbody>' +
        rows.map(row => '<tr>' + columns.map(c => '<td>' + (c.value(row) ?? '') + '</td>').join('') + '</tr>').join('') + '</tbody></table>';
    }
    async function loadAll() {
      const [agentsResponse, draftsResponse] = await Promise.all([
        fetch('/agents', { headers: headers() }),
        fetch('/studio/agent-drafts', { headers: headers() })
      ]);
      const agents = agentsResponse.ok ? (await agentsResponse.json()).agents : [];
      const drafts = draftsResponse.ok ? (await draftsResponse.json()).drafts : [];
      document.getElementById('agents').innerHTML = table(agents, [
        { label: 'Name', value: r => r.name },
        { label: 'Owner', value: r => r.owner },
        { label: 'Status', value: r => r.status },
        { label: 'Risk', value: r => r.risk_class }
      ]);
      document.getElementById('drafts').innerHTML = table(drafts, [
        { label: 'Name', value: r => r.name },
        { label: 'Owner', value: r => r.owner },
        { label: 'Status', value: r => r.status },
        { label: 'Version', value: r => r.manifest?.version }
      ]);
    }
    loadAll();
  </script>
</body>
</html>
        """

    @app.post("/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
    def create_agent(
        request: Request,
        agent_request: CreateAgentRequest,
        tenant_id: TenantIdHeader,
    ) -> AgentResponse:
        registry_service = _registry_from_request(request)
        return _map_registry_errors(
            lambda: AgentResponse(
                agent=registry_service.create_agent(
                    tenant_id=tenant_id,
                    name=agent_request.name,
                    owner=agent_request.owner,
                    risk_class=agent_request.risk_class,
                )
            )
        )

    @app.get("/agents", response_model=AgentListResponse)
    def list_agents(request: Request, tenant_id: TenantIdHeader) -> AgentListResponse:
        registry_service = _registry_from_request(request)
        return AgentListResponse(agents=registry_service.list_agents(tenant_id))

    @app.get("/agents/{agent_id}", response_model=AgentResponse)
    def get_agent(request: Request, agent_id: UUID, tenant_id: TenantIdHeader) -> AgentResponse:
        registry_service = _registry_from_request(request)
        return _map_registry_errors(
            lambda: AgentResponse(agent=registry_service.get_agent(tenant_id, agent_id))
        )

    @app.post(
        "/agents/{agent_id}/versions",
        response_model=AgentVersionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def publish_agent_version(
        request: Request,
        agent_id: UUID,
        version_request: PublishAgentVersionRequest,
        tenant_id: TenantIdHeader,
    ) -> AgentVersionResponse:
        registry_service = _registry_from_request(request)
        return _map_registry_errors(
            lambda: AgentVersionResponse(
                version=registry_service.publish_version(
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    manifest=version_request.manifest,
                )
            )
        )

    @app.get("/agents/{agent_id}/versions", response_model=AgentVersionListResponse)
    def list_agent_versions(
        request: Request,
        agent_id: UUID,
        tenant_id: TenantIdHeader,
    ) -> AgentVersionListResponse:
        registry_service = _registry_from_request(request)
        return _map_registry_errors(
            lambda: AgentVersionListResponse(
                versions=registry_service.list_versions(tenant_id, agent_id)
            )
        )

    @app.post("/agents/{agent_id}/deprecate", response_model=AgentResponse)
    def deprecate_agent(request: Request, agent_id: UUID, tenant_id: TenantIdHeader) -> AgentResponse:
        registry_service = _registry_from_request(request)
        return _map_registry_errors(
            lambda: AgentResponse(agent=registry_service.deprecate_agent(tenant_id, agent_id))
        )

    @app.post(
        "/studio/agent-drafts",
        response_model=AgentDraftResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_agent_draft(
        request: Request,
        draft_request: CreateAgentDraftRequest,
        tenant_id: TenantIdHeader,
    ) -> AgentDraftResponse:
        studio_service = _studio_from_request(request)
        return AgentDraftResponse(
            draft=studio_service.create_draft(
                tenant_id=tenant_id,
                name=draft_request.name,
                owner=draft_request.owner,
                manifest=draft_request.manifest,
                risk_class=draft_request.risk_class,
            )
        )

    @app.get("/studio/agent-drafts", response_model=AgentDraftListResponse)
    def list_agent_drafts(request: Request, tenant_id: TenantIdHeader) -> AgentDraftListResponse:
        studio_service = _studio_from_request(request)
        return AgentDraftListResponse(drafts=studio_service.list_drafts(tenant_id))

    @app.get("/studio/agent-drafts/{draft_id}", response_model=AgentDraftResponse)
    def get_agent_draft(
        request: Request,
        draft_id: UUID,
        tenant_id: TenantIdHeader,
    ) -> AgentDraftResponse:
        studio_service = _studio_from_request(request)
        return _map_studio_errors(
            lambda: AgentDraftResponse(draft=studio_service.get_draft(tenant_id, draft_id))
        )

    @app.put("/studio/agent-drafts/{draft_id}", response_model=AgentDraftResponse)
    def update_agent_draft(
        request: Request,
        draft_id: UUID,
        draft_request: UpdateAgentDraftRequest,
        tenant_id: TenantIdHeader,
    ) -> AgentDraftResponse:
        studio_service = _studio_from_request(request)
        return _map_studio_errors(
            lambda: AgentDraftResponse(
                draft=studio_service.update_draft(
                    tenant_id=tenant_id,
                    draft_id=draft_id,
                    name=draft_request.name,
                    owner=draft_request.owner,
                    manifest=draft_request.manifest,
                    risk_class=draft_request.risk_class,
                )
            )
        )

    @app.post(
        "/studio/agent-drafts/{draft_id}/validate",
        response_model=AgentDraftValidationResponse,
    )
    def validate_agent_draft(
        request: Request,
        draft_id: UUID,
        tenant_id: TenantIdHeader,
    ) -> AgentDraftValidationResponse:
        studio_service = _studio_from_request(request)
        return _map_studio_errors(
            lambda: AgentDraftValidationResponse(
                validation=studio_service.validate_draft(tenant_id, draft_id)
            )
        )

    @app.post(
        "/studio/agent-drafts/{draft_id}/publish",
        response_model=AgentVersionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def publish_agent_draft(
        request: Request,
        draft_id: UUID,
        tenant_id: TenantIdHeader,
    ) -> AgentVersionResponse:
        studio_service = _studio_from_request(request)
        return _map_studio_errors(
            lambda: _map_registry_errors(
                lambda: AgentVersionResponse(
                    version=studio_service.publish_draft(tenant_id, draft_id)
                )
            )
        )

    return app


def _registry_from_request(request: Request) -> AgentRegistryService:
    return request.app.state.registry


def _studio_from_request(request: Request) -> AgentStudioService:
    return request.app.state.studio


def _map_registry_errors(operation: Callable[[], object]):
    try:
        return operation()
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (DuplicateAgentNameError, DuplicateAgentVersionError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


def _map_studio_errors(operation: Callable[[], object]):
    try:
        return operation()
    except AgentDraftNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AgentDraftAlreadyPublishedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc



def _configure_optional_api_key_auth(app: FastAPI) -> None:
    api_key = os.getenv("AGENTIC_PLATFORM_API_KEY")
    if not api_key:
        return

    @app.middleware("http")
    async def api_key_middleware(request: Request, call_next):
        if request.url.path in {"/health", "/studio", "/studio/evaluations", "/studio/deployments"}:
            return await call_next(request)
        if request.headers.get("X-API-Key") != api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
        return await call_next(request)


app = create_app()
