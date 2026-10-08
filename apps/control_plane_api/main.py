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
        return r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Enterprise Agentic Platform</title>
  <style>
    :root { color-scheme: light; font-family: Inter, Segoe UI, Arial, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f4f6f9; color: #172033; }
    .shell { min-height: 100vh; display: grid; grid-template-columns: 260px 1fr; }
    aside { background: #111827; color: #ffffff; padding: 18px 14px; position: sticky; top: 0; height: 100vh; }
    .brand { font-size: 18px; font-weight: 700; line-height: 1.25; margin: 4px 8px 18px; }
    .subtitle { color: #b9c3d4; font-size: 12px; margin: -8px 8px 16px; line-height: 1.35; }
    nav { display: grid; gap: 6px; }
    nav button { width: 100%; text-align: left; color: #d9e2f1; background: transparent; border: 1px solid transparent; border-radius: 7px; padding: 10px 11px; cursor: pointer; font-size: 13px; }
    nav button.active, nav button:hover { background: #243247; color: #ffffff; border-color: #37465c; }
    header { background: #ffffff; border-bottom: 1px solid #d8dee8; padding: 14px 22px; display: flex; gap: 14px; align-items: end; flex-wrap: wrap; }
    header h1 { margin: 0 18px 0 0; font-size: 22px; min-width: 260px; }
    main { padding: 20px 22px 36px; display: grid; gap: 16px; }
    .toolbar { display: flex; gap: 10px; align-items: end; flex-wrap: wrap; }
    label { font-size: 12px; color: #526074; display: block; margin-bottom: 4px; }
    input, select, textarea { width: 100%; border: 1px solid #b8c1cf; border-radius: 7px; padding: 9px 10px; font: inherit; background: #ffffff; color: #172033; }
    input, select { height: 38px; }
    textarea { min-height: 96px; resize: vertical; }
    button.primary, a.primary { height: 38px; border: 1px solid #1f334f; border-radius: 7px; background: #1f334f; color: #ffffff; padding: 0 13px; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; justify-content: center; font-size: 13px; }
    button.secondary { height: 38px; border: 1px solid #b8c1cf; border-radius: 7px; background: #ffffff; color: #243247; padding: 0 13px; cursor: pointer; }
    .panel { display: none; }
    .panel.active { display: grid; gap: 16px; }
    .grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); }
    .card { background: #ffffff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; }
    .card h2 { margin: 0 0 12px; font-size: 16px; }
    .card h3 { margin: 0 0 10px; font-size: 14px; }
    .form-grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }
    .span-all { grid-column: 1 / -1; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 8px; border-bottom: 1px solid #edf1f6; vertical-align: top; }
    th { color: #526074; font-weight: 650; }
    .empty, .hint { color: #697386; font-size: 13px; line-height: 1.45; }
    .status { min-height: 20px; color: #355c2d; font-size: 13px; margin-top: 10px; }
    .error { color: #a33a2a; }
    .kpi { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
    .metric { background: #ffffff; border: 1px solid #d8dee8; border-radius: 8px; padding: 14px; }
    .metric strong { display: block; font-size: 24px; margin-top: 4px; }
    .pill { display: inline-block; border: 1px solid #cbd4e2; border-radius: 999px; padding: 3px 8px; font-size: 12px; color: #3d4b60; background: #f8fafc; }
    @media (max-width: 860px) { .shell { grid-template-columns: 1fr; } aside { position: relative; height: auto; } nav { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); } header h1 { min-width: auto; } }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <div class="brand">Enterprise Agentic Platform</div>
      <div class="subtitle">Agent Studio, tools, prompts, evaluation, deployment, governance, and operations.</div>
      <nav aria-label="Studio modules">
        <button class="active" data-tab="dashboard">Dashboard</button>
        <button data-tab="agents">Create Agent</button>
        <button data-tab="drafts">Agent Designer</button>
        <button data-tab="tools">Tool Config</button>
        <button data-tab="prompts">Prompt Editor</button>
        <button data-tab="evaluation">Evaluation</button>
        <button data-tab="deployment">Deployment</button>
        <button data-tab="governance">Governance</button>
        <button data-tab="operations">Operations</button>
      </nav>
    </aside>
    <div>
      <header>
        <h1>Agent Studio</h1>
        <div class="toolbar">
          <div><label for="tenant">Tenant</label><input id="tenant" value="tenant-a" /></div>
          <div><label for="apiKey">API Key</label><input id="apiKey" type="password" placeholder="optional" /></div>
          <button class="primary" onclick="loadAll()">Refresh</button>
        </div>
      </header>
      <main>
        <section id="dashboard" class="panel active">
          <div class="kpi">
            <div class="metric">Agents<strong id="agentCount">0</strong></div>
            <div class="metric">Drafts<strong id="draftCount">0</strong></div>
            <div class="metric">Tools<strong id="toolCount">0</strong></div>
            <div class="metric">Open Gates<strong>4</strong></div>
          </div>
          <div class="grid">
            <div class="card"><h2>Platform Workbench</h2><p class="hint">Use the left navigation to create agents, design manifests, configure tools, edit prompts, run evaluations, review deployment gates, and inspect governance controls.</p></div>
            <div class="card"><h2>Quick Links</h2><p><a class="primary" href="/studio/evaluations">Evaluation Workspace</a> <a class="primary" href="/studio/deployments">Deployment Console</a> <a class="primary" href="/docs">API Docs</a></p></div>
          </div>
        </section>

        <section id="agents" class="panel">
          <div class="grid">
            <div class="card">
              <h2>Create Agent</h2>
              <div class="form-grid">
                <div><label for="agentName">Name</label><input id="agentName" value="Customer Support Agent" /></div>
                <div><label for="agentOwner">Owner</label><input id="agentOwner" value="ai-platform-team" /></div>
                <div><label for="agentRisk">Risk</label><select id="agentRisk"><option>low</option><option selected>medium</option><option>high</option><option>critical</option></select></div>
              </div>
              <button class="primary" onclick="createAgent()">Create Agent</button>
              <div id="agentStatus" class="status"></div>
            </div>
            <div class="card"><h2>Agent Registry</h2><div id="agentsTable" class="empty">No agents loaded.</div></div>
          </div>
        </section>

        <section id="drafts" class="panel">
          <div class="grid">
            <div class="card">
              <h2>Agent Designer</h2>
              <div class="form-grid">
                <div><label for="draftName">Draft Name</label><input id="draftName" value="Claims Research Agent" /></div>
                <div><label for="draftOwner">Owner</label><input id="draftOwner" value="claims-team" /></div>
                <div><label for="draftVersion">Version</label><input id="draftVersion" value="0.1.0" /></div>
                <div><label for="draftRisk">Risk</label><select id="draftRisk"><option>low</option><option selected>medium</option><option>high</option><option>critical</option></select></div>
                <div><label for="draftRole">Role</label><input id="draftRole" value="claims-research-specialist" /></div>
                <div><label for="draftGoal">Goal</label><input id="draftGoal" value="research claim context with governed tools and RAG" /></div>
              </div>
              <button class="primary" onclick="createDraft()">Create Draft</button>
              <div id="draftStatus" class="status"></div>
            </div>
            <div class="card"><h2>Drafts</h2><div id="draftsTable" class="empty">No drafts loaded.</div></div>
          </div>
        </section>

        <section id="tools" class="panel">
          <div class="grid">
            <div class="card">
              <h2>Tool Config</h2>
              <div class="form-grid">
                <div><label for="toolName">Tool Name</label><input id="toolName" value="crm.lookup" /></div>
                <div><label for="toolRisk">Risk</label><select id="toolRisk"><option>low</option><option selected>medium</option><option>high</option><option>critical</option></select></div>
                <div><label for="toolTimeout">Timeout Seconds</label><input id="toolTimeout" type="number" value="30" /></div>
                <div class="span-all"><label for="toolAgents">Allowed Agents</label><input id="toolAgents" value="agent.customer-support" /></div>
                <div class="span-all"><label for="toolActions">Allowed Actions</label><input id="toolActions" value="read,search" /></div>
                <div class="span-all"><label for="toolDescription">Description</label><textarea id="toolDescription">Lookup customer profile records with audited read-only access.</textarea></div>
              </div>
              <button class="primary" onclick="saveTool()">Save Tool Config</button>
              <div id="toolStatus" class="status"></div>
            </div>
            <div class="card"><h2>Configured Tools</h2><div id="toolsTable" class="empty">No tools configured.</div></div>
          </div>
        </section>

        <section id="prompts" class="panel">
          <div class="grid">
            <div class="card">
              <h2>Prompt Editor</h2>
              <div class="form-grid">
                <div><label for="promptName">Template Name</label><input id="promptName" value="support-triage" /></div>
                <div><label for="promptVersion">Version</label><input id="promptVersion" value="1.0.0" /></div>
                <div class="span-all"><label for="promptText">Prompt</label><textarea id="promptText">You are a governed enterprise agent. Answer using only approved context for {customer_id}.</textarea></div>
              </div>
              <button class="primary" onclick="savePrompt()">Save Prompt</button>
              <div id="promptStatus" class="status"></div>
            </div>
            <div class="card"><h2>Prompt Assets</h2><div id="promptsTable" class="empty">No prompts saved.</div></div>
          </div>
        </section>

        <section id="evaluation" class="panel">
          <div class="grid">
            <div class="card"><h2>Evaluation Workspace</h2><p class="hint">Configure offline golden datasets, prompt regression, user feedback, human scoring, LLM-as-judge, and safety checks.</p><table><thead><tr><th>Suite</th><th>Mode</th><th>Status</th></tr></thead><tbody><tr><td>Golden Dataset Smoke</td><td>offline</td><td><span class="pill">ready</span></td></tr><tr><td>Safety Regression</td><td>safety</td><td><span class="pill">ready</span></td></tr><tr><td>Prompt Regression</td><td>judge</td><td><span class="pill">planned</span></td></tr></tbody></table></div>
            <div class="card"><h2>Quality Gates</h2><p class="hint">Minimum score: 0.80. Safety gates: groundedness, hallucination, toxicity, PII leakage, and prompt injection resilience.</p><a class="primary" href="/studio/evaluations">Open full evaluation page</a></div>
          </div>
        </section>

        <section id="deployment" class="panel">
          <div class="grid">
            <div class="card"><h2>Deployment Console</h2><table><thead><tr><th>Gate</th><th>Status</th><th>Evidence</th></tr></thead><tbody><tr><td>Policy</td><td><span class="pill">passed</span></td><td>tenant and risk policy</td></tr><tr><td>Evaluation</td><td><span class="pill">pending</span></td><td>golden dataset result</td></tr><tr><td>Responsible AI</td><td><span class="pill">passed</span></td><td>model risk record</td></tr><tr><td>AISecOps</td><td><span class="pill">passed</span></td><td>monitoring signals</td></tr></tbody></table></div>
            <div class="card"><h2>Target</h2><div class="form-grid"><div><label>Environment</label><select><option>local</option><option>dev</option><option>test</option><option>prod</option></select></div><div><label>Runtime URL</label><input value="http://localhost:8002" /></div></div><p><a class="primary" href="/studio/deployments">Open deployment page</a></p></div>
          </div>
        </section>

        <section id="governance" class="panel">
          <div class="grid">
            <div class="card"><h2>Responsible AI</h2><p class="hint">Fairness testing, bias detection, sensitive attribute monitoring, explainability reports, model risk tracking, and regulatory evidence generation.</p></div>
            <div class="card"><h2>AISecOps</h2><p class="hint">Prompt attack monitoring, agent behavior monitoring, RAG poisoning monitoring, model drift detection, tool abuse detection, and anomaly detection.</p></div>
            <div class="card"><h2>Memory Governance</h2><table><thead><tr><th>Memory Type</th><th>Retention</th></tr></thead><tbody><tr><td>Session</td><td>24 hrs</td></tr><tr><td>Conversation</td><td>90 days</td></tr><tr><td>Agent Working Memory</td><td>Runtime only</td></tr><tr><td>Semantic Memory</td><td>Policy controlled</td></tr><tr><td>Human Decisions</td><td>7 years</td></tr></tbody></table></div>
          </div>
        </section>

        <section id="operations" class="panel">
          <div class="grid">
            <div class="card"><h2>AI FinOps</h2><p class="hint">Track cost per tenant, agent, workflow, department, token trends, budgets, chargeback, and showback.</p></div>
            <div class="card"><h2>Runtime Operations</h2><p class="hint">Observe traces, metrics, event bus activity, background worker jobs, Kubernetes readiness, and security posture.</p></div>
            <div class="card"><h2>Local APIs</h2><p><a class="primary" href="/docs">Control Plane API docs</a></p><p class="hint">Runtime API is usually available separately on port 8002 when started.</p></div>
          </div>
        </section>
      </main>
    </div>
  </div>
  <script>
    const state = { agents: [], drafts: [], tools: JSON.parse(localStorage.getItem('studioTools') || '[]'), prompts: JSON.parse(localStorage.getItem('studioPrompts') || '[]') };
    document.querySelectorAll('nav button').forEach(button => button.addEventListener('click', () => showTab(button.dataset.tab)));
    function showTab(tab) {
      document.querySelectorAll('nav button').forEach(button => button.classList.toggle('active', button.dataset.tab === tab));
      document.querySelectorAll('.panel').forEach(panel => panel.classList.toggle('active', panel.id === tab));
    }
    function requestHeaders() {
      const headers = { 'X-Tenant-ID': document.getElementById('tenant').value, 'Content-Type': 'application/json' };
      const apiKey = document.getElementById('apiKey').value;
      if (apiKey) headers['X-API-Key'] = apiKey;
      return headers;
    }
    function table(rows, columns) {
      if (!rows.length) return '<p class="empty">Nothing found.</p>';
      return '<table><thead><tr>' + columns.map(c => '<th>' + c.label + '</th>').join('') + '</tr></thead><tbody>' + rows.map(row => '<tr>' + columns.map(c => '<td>' + (c.value(row) ?? '') + '</td>').join('') + '</tr>').join('') + '</tbody></table>';
    }
    function setStatus(id, text, isError = false) {
      const element = document.getElementById(id);
      element.textContent = text;
      element.classList.toggle('error', isError);
    }
    async function loadAll() {
      const [agentsResponse, draftsResponse] = await Promise.all([
        fetch('/agents', { headers: requestHeaders() }),
        fetch('/studio/agent-drafts', { headers: requestHeaders() })
      ]);
      state.agents = agentsResponse.ok ? (await agentsResponse.json()).agents : [];
      state.drafts = draftsResponse.ok ? (await draftsResponse.json()).drafts : [];
      renderAll();
    }
    function renderAll() {
      document.getElementById('agentCount').textContent = state.agents.length;
      document.getElementById('draftCount').textContent = state.drafts.length;
      document.getElementById('toolCount').textContent = state.tools.length;
      document.getElementById('agentsTable').innerHTML = table(state.agents, [
        { label: 'Name', value: r => r.name }, { label: 'Owner', value: r => r.owner }, { label: 'Status', value: r => r.status }, { label: 'Risk', value: r => r.risk_class }
      ]);
      document.getElementById('draftsTable').innerHTML = table(state.drafts, [
        { label: 'Name', value: r => r.name }, { label: 'Owner', value: r => r.owner }, { label: 'Status', value: r => r.status }, { label: 'Version', value: r => r.manifest?.version }
      ]);
      document.getElementById('toolsTable').innerHTML = table(state.tools, [
        { label: 'Name', value: r => r.name }, { label: 'Risk', value: r => r.risk }, { label: 'Agents', value: r => r.agents }, { label: 'Actions', value: r => r.actions }
      ]);
      document.getElementById('promptsTable').innerHTML = table(state.prompts, [
        { label: 'Name', value: r => r.name }, { label: 'Version', value: r => r.version }, { label: 'Variables', value: r => (r.text.match(/\{[^}]+\}/g) || []).join(', ') }
      ]);
    }
    async function createAgent() {
      const payload = { name: document.getElementById('agentName').value, owner: document.getElementById('agentOwner').value, risk_class: document.getElementById('agentRisk').value };
      const response = await fetch('/agents', { method: 'POST', headers: requestHeaders(), body: JSON.stringify(payload) });
      if (!response.ok) { setStatus('agentStatus', 'Create failed: ' + await response.text(), true); return; }
      setStatus('agentStatus', 'Agent created.');
      await loadAll();
    }
    async function createDraft() {
      const name = document.getElementById('draftName').value;
      const manifest = { id: 'agent.' + name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, ''), name, version: document.getElementById('draftVersion').value, role: document.getElementById('draftRole').value, goal: document.getElementById('draftGoal').value, model: { provider: 'mock', model: 'mock-model' } };
      const payload = { name, owner: document.getElementById('draftOwner').value, risk_class: document.getElementById('draftRisk').value, manifest };
      const response = await fetch('/studio/agent-drafts', { method: 'POST', headers: requestHeaders(), body: JSON.stringify(payload) });
      if (!response.ok) { setStatus('draftStatus', 'Draft failed: ' + await response.text(), true); return; }
      setStatus('draftStatus', 'Draft created.');
      await loadAll();
    }
    function saveTool() {
      state.tools.push({ name: document.getElementById('toolName').value, risk: document.getElementById('toolRisk').value, agents: document.getElementById('toolAgents').value, actions: document.getElementById('toolActions').value, timeout: document.getElementById('toolTimeout').value, description: document.getElementById('toolDescription').value });
      localStorage.setItem('studioTools', JSON.stringify(state.tools));
      setStatus('toolStatus', 'Tool configuration saved locally. Backend tool APIs are the next integration step.');
      renderAll();
    }
    function savePrompt() {
      state.prompts.push({ name: document.getElementById('promptName').value, version: document.getElementById('promptVersion').value, text: document.getElementById('promptText').value });
      localStorage.setItem('studioPrompts', JSON.stringify(state.prompts));
      setStatus('promptStatus', 'Prompt saved locally. Backend prompt APIs are the next integration step.');
      renderAll();
    }
    renderAll();
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
