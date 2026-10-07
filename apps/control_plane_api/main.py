from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Request, status

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

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "control-plane-api"}

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


app = create_app()
