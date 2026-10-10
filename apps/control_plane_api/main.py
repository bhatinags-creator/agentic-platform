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
    AgentInteractionListResponse,
    AgentInteractionResponse,
    AgentListResponse,
    AgentResponse,
    AgentTestRunResponse,
    AgentVersionListResponse,
    AgentVersionResponse,
    CreateAgentDraftRequest,
    CreateAgentRequest,
    CreatePromptTemplateRequest,
    CreateRuleRequest,
    CreateToolRequest,
    InvokeAgentDraftRequest,
    ModelProfileListResponse,
    ModelProfileResponse,
    PromptTemplateListResponse,
    PromptTemplateVersionResponse,
    PublishAgentVersionRequest,
    RuleListResponse,
    RunAgentDraftTestsRequest,
    SaveModelProfileRequest,
    SaveWorkflowRequest,
    TestToolRequest,
    TestToolResponse,
    ToolListResponse,
    UpdateAgentDraftRequest,
    WorkflowListResponse,
)
from apps.control_plane_api.studio_ui import render_agent_studio
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
from services.agent_studio.sqlite_repository import (
    SQLiteAgentDraftRepository,
    SQLiteAgentInteractionRepository,
)
from services.model_config.service import ModelConfigService
from services.prompt_management.service import PromptManagementService, SQLitePromptRepository
from services.runtime_execution.service import RuntimeExecutionFailedError, RuntimeExecutionService
from services.studio_assets.service import SQLiteStudioAssetRepository, StudioAssetService
from services.tool_gateway.service import (
    SQLiteToolRepository,
    ToolGatewayService,
    ToolInvocationDeniedError,
    ToolInvocationExecutionError,
    ToolNotFoundError,
    ToolRegistryService,
)

TenantIdHeader = Annotated[str, Header(alias="X-Tenant-ID")]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "agentic_platform.db"


def build_default_registry() -> AgentRegistryService:
    database_path = Path(os.getenv("AGENTIC_PLATFORM_DB_PATH", str(DEFAULT_DATABASE_PATH)))
    return AgentRegistryService(repository=SQLiteAgentRegistryRepository(database_path))


def build_default_studio(
    registry: AgentRegistryService,
    tool_registry: ToolRegistryService,
    model_config: ModelConfigService,
) -> AgentStudioService:
    database_path = Path(os.getenv("AGENTIC_PLATFORM_DB_PATH", str(DEFAULT_DATABASE_PATH)))
    return AgentStudioService(
        registry=registry,
        repository=SQLiteAgentDraftRepository(database_path),
        interaction_repository=SQLiteAgentInteractionRepository(database_path),
        runtime=RuntimeExecutionService(
            tool_gateway=ToolGatewayService(registry=tool_registry),
        ),
        model_config=model_config,
    )


def build_default_model_config() -> ModelConfigService:
    database_path = Path(os.getenv("AGENTIC_PLATFORM_DB_PATH", str(DEFAULT_DATABASE_PATH)))
    return ModelConfigService(database_path)


def build_default_prompt_service() -> PromptManagementService:
    database_path = Path(os.getenv("AGENTIC_PLATFORM_DB_PATH", str(DEFAULT_DATABASE_PATH)))
    return PromptManagementService(repository=SQLitePromptRepository(database_path))


def build_default_tool_registry() -> ToolRegistryService:
    database_path = Path(os.getenv("AGENTIC_PLATFORM_DB_PATH", str(DEFAULT_DATABASE_PATH)))
    return ToolRegistryService(repository=SQLiteToolRepository(database_path))


def build_default_studio_assets() -> StudioAssetService:
    database_path = Path(os.getenv("AGENTIC_PLATFORM_DB_PATH", str(DEFAULT_DATABASE_PATH)))
    return StudioAssetService(repository=SQLiteStudioAssetRepository(database_path))


def create_app(
    registry: AgentRegistryService | None = None,
    studio: AgentStudioService | None = None,
    prompt_service: PromptManagementService | None = None,
    tool_registry: ToolRegistryService | None = None,
    studio_assets: StudioAssetService | None = None,
    model_config: ModelConfigService | None = None,
) -> FastAPI:
    app = FastAPI(title="Agentic Platform Control Plane API", version="0.1.0")
    app.state.registry = registry or build_default_registry()
    app.state.prompt_service = prompt_service or build_default_prompt_service()
    app.state.tool_registry = tool_registry or build_default_tool_registry()
    app.state.model_config = model_config or build_default_model_config()
    app.state.studio = studio or build_default_studio(
        app.state.registry,
        app.state.tool_registry,
        app.state.model_config,
    )
    app.state.studio_assets = studio_assets or build_default_studio_assets()
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
        return render_agent_studio()

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
        "/studio/agent-drafts/{draft_id}/test-runs",
        response_model=AgentTestRunResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def run_agent_draft_tests(
        request: Request,
        draft_id: UUID,
        test_request: RunAgentDraftTestsRequest,
        tenant_id: TenantIdHeader,
    ) -> AgentTestRunResponse:
        studio_service = _studio_from_request(request)
        return _map_studio_errors(
            lambda: AgentTestRunResponse(
                result=studio_service.run_test_harness(
                    tenant_id=tenant_id,
                    draft_id=draft_id,
                    test_cases=[test_case.model_dump() for test_case in test_request.test_cases],
                )
            )
        )

    @app.post(
        "/studio/agent-drafts/{draft_id}/interactions",
        response_model=AgentInteractionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def invoke_agent_draft(
        request: Request,
        draft_id: UUID,
        interaction_request: InvokeAgentDraftRequest,
        tenant_id: TenantIdHeader,
    ) -> AgentInteractionResponse:
        studio_service = _studio_from_request(request)
        try:
            return AgentInteractionResponse(
                interaction=await studio_service.invoke_draft_agent(
                    tenant_id=tenant_id,
                    draft_id=draft_id,
                    query=interaction_request.query,
                )
            )
        except AgentDraftNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except AgentDraftAlreadyPublishedError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except RuntimeExecutionFailedError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    @app.get(
        "/studio/agent-drafts/{draft_id}/interactions",
        response_model=AgentInteractionListResponse,
    )
    def list_agent_draft_interactions(
        request: Request,
        draft_id: UUID,
        tenant_id: TenantIdHeader,
    ) -> AgentInteractionListResponse:
        studio_service = _studio_from_request(request)
        return AgentInteractionListResponse(
            interactions=studio_service.list_interactions(tenant_id=tenant_id, draft_id=draft_id)
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


    @app.post(
        "/studio/prompts",
        response_model=PromptTemplateVersionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_prompt_template(
        request: Request,
        prompt_request: CreatePromptTemplateRequest,
        tenant_id: TenantIdHeader,
    ) -> PromptTemplateVersionResponse:
        prompt_service = _prompt_service_from_request(request)
        template = prompt_service.create_template(
            tenant_id=tenant_id,
            name=prompt_request.name,
            owner=prompt_request.owner,
            description=prompt_request.description,
        )
        version = prompt_service.create_version(
            tenant_id=tenant_id,
            template_id=template.template_id,
            version=prompt_request.version,
            template_text=prompt_request.template_text,
        )
        return PromptTemplateVersionResponse(template=template, version=version)

    @app.get("/studio/prompts", response_model=PromptTemplateListResponse)
    def list_prompt_templates(request: Request, tenant_id: TenantIdHeader) -> PromptTemplateListResponse:
        prompt_service = _prompt_service_from_request(request)
        prompts = []
        for template in prompt_service.list_templates(tenant_id):
            versions = prompt_service.list_versions(tenant_id, template.template_id)
            prompts.append({"template": template, "versions": versions})
        return PromptTemplateListResponse(prompts=prompts)

    @app.post(
        "/studio/model-profiles",
        response_model=ModelProfileResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def save_model_profile(
        request: Request,
        profile_request: SaveModelProfileRequest,
        tenant_id: TenantIdHeader,
    ) -> ModelProfileResponse:
        model_config = _model_config_from_request(request)
        return ModelProfileResponse(
            profile=model_config.save_profile(
                tenant_id=tenant_id,
                profile_id=profile_request.profile_id,
                display_name=profile_request.display_name,
                provider=profile_request.provider,
                model=profile_request.model,
                api_key=profile_request.api_key,
            )
        )

    @app.get("/studio/model-profiles", response_model=ModelProfileListResponse)
    def list_model_profiles(request: Request, tenant_id: TenantIdHeader) -> ModelProfileListResponse:
        model_config = _model_config_from_request(request)
        return ModelProfileListResponse(profiles=model_config.list_profiles(tenant_id))

    @app.delete("/studio/model-profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_model_profile(request: Request, profile_id: str, tenant_id: TenantIdHeader) -> None:
        model_config = _model_config_from_request(request)
        model_config.delete_profile(tenant_id, profile_id)

    @app.post("/studio/tools", status_code=status.HTTP_201_CREATED)
    def create_tool(
        request: Request,
        tool_request: CreateToolRequest,
        tenant_id: TenantIdHeader,
    ):
        tool_registry = _tool_registry_from_request(request)
        return {
            "tool": tool_registry.register_tool(
                tenant_id=tenant_id,
                name=tool_request.name,
                description=tool_request.description,
                implementation_type=tool_request.implementation_type,
                endpoint_url=tool_request.endpoint_url,
                method=tool_request.method,
                auth_type=tool_request.auth_type,
                input_schema=tool_request.input_schema,
                output_schema=tool_request.output_schema,
                risk_class=tool_request.risk_class,
                allowed_agents=tool_request.allowed_agents,
                allowed_actions=tool_request.allowed_actions,
                timeout_seconds=tool_request.timeout_seconds,
            )
        }

    @app.get("/studio/tools", response_model=ToolListResponse)
    def list_tools(request: Request, tenant_id: TenantIdHeader) -> ToolListResponse:
        tool_registry = _tool_registry_from_request(request)
        tenant_tools = [
            tool
            for tool in tool_registry.list_tools(tenant_id)
            if tool.tenant_id == tenant_id
            and not (tool.tenant_id == "default" and tool.name == "mvp.echo")
        ]
        return ToolListResponse(tools=tenant_tools)

    @app.post("/studio/tools/{tool_name}/test", response_model=TestToolResponse)
    async def test_tool(
        request: Request,
        tool_name: str,
        test_request: TestToolRequest,
        tenant_id: TenantIdHeader,
    ) -> TestToolResponse:
        tool_registry = _tool_registry_from_request(request)
        tool_gateway = ToolGatewayService(registry=tool_registry)
        payload = {
            **test_request.payload,
            **({"action": test_request.action} if test_request.action else {}),
        }
        try:
            result = await tool_gateway.invoke(
                tool_name,
                payload,
                {
                    "tenant_id": tenant_id,
                    "agent_id": test_request.agent_id,
                    "trace_id": "studio-tool-test",
                },
            )
            return TestToolResponse(result=result)
        except ToolNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ToolInvocationDeniedError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
        except ToolInvocationExecutionError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    @app.post("/studio/rules", status_code=status.HTTP_201_CREATED)
    def create_rule(
        request: Request,
        rule_request: CreateRuleRequest,
        tenant_id: TenantIdHeader,
    ):
        studio_assets = _studio_assets_from_request(request)
        return {
            "rule": studio_assets.create_rule(
                tenant_id=tenant_id,
                name=rule_request.name,
                condition=rule_request.condition,
                decision=rule_request.decision,
            )
        }

    @app.get("/studio/rules", response_model=RuleListResponse)
    def list_rules(request: Request, tenant_id: TenantIdHeader) -> RuleListResponse:
        studio_assets = _studio_assets_from_request(request)
        return RuleListResponse(rules=studio_assets.list_rules(tenant_id))

    @app.post("/studio/workflows", status_code=status.HTTP_201_CREATED)
    def save_workflow(
        request: Request,
        workflow_request: SaveWorkflowRequest,
        tenant_id: TenantIdHeader,
    ):
        studio_assets = _studio_assets_from_request(request)
        return {
            "workflow": studio_assets.save_workflow(
                tenant_id=tenant_id,
                agent_id=workflow_request.agent_id,
                name=workflow_request.name,
                nodes=[node.model_dump() for node in workflow_request.nodes],
                workflow_id=workflow_request.workflow_id,
            )
        }

    @app.get("/studio/workflows", response_model=WorkflowListResponse)
    def list_workflows(
        request: Request,
        tenant_id: TenantIdHeader,
        agent_id: str | None = None,
    ) -> WorkflowListResponse:
        studio_assets = _studio_assets_from_request(request)
        return WorkflowListResponse(workflows=studio_assets.list_workflows(tenant_id, agent_id))

    return app


def _registry_from_request(request: Request) -> AgentRegistryService:
    return request.app.state.registry


def _studio_from_request(request: Request) -> AgentStudioService:
    return request.app.state.studio




def _prompt_service_from_request(request: Request) -> PromptManagementService:
    return request.app.state.prompt_service


def _tool_registry_from_request(request: Request) -> ToolRegistryService:
    return request.app.state.tool_registry


def _studio_assets_from_request(request: Request) -> StudioAssetService:
    return request.app.state.studio_assets


def _model_config_from_request(request: Request) -> ModelConfigService:
    return request.app.state.model_config

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
