from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from apps.runtime_api.schemas import AgentRunListResponse, AgentRunResponse, StartRunRequest
from services.audit_service.service import AuditService, SQLiteAuditRepository
from services.finops_service.service import AIFinOpsService, SQLiteFinOpsRepository
from services.memory_governance.service import MemoryGovernanceService, SQLiteMemoryRepository
from services.runtime_execution.service import (
    AgentRunNotFoundError,
    RuntimeExecutionFailedError,
    RuntimeExecutionService,
    RuntimePolicyDeniedError,
)
from services.runtime_execution.sqlite_repository import SQLiteAgentRunRepository

TenantIdHeader = Annotated[str, Header(alias="X-Tenant-ID")]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_DATABASE_PATH = PROJECT_ROOT / "data" / "agentic_platform_runtime.db"


def build_default_runtime() -> RuntimeExecutionService:
    database_path = Path(
        os.getenv("AGENTIC_PLATFORM_RUNTIME_DB_PATH", str(DEFAULT_RUNTIME_DATABASE_PATH))
    )
    return RuntimeExecutionService(
        repository=SQLiteAgentRunRepository(database_path),
        audit_service=AuditService(repository=SQLiteAuditRepository(database_path)),
        finops_service=AIFinOpsService(repository=SQLiteFinOpsRepository(database_path)),
        memory_governance=MemoryGovernanceService(repository=SQLiteMemoryRepository(database_path)),
    )


def create_app(runtime: RuntimeExecutionService | None = None) -> FastAPI:
    app = FastAPI(title="Agentic Platform Runtime API", version="0.1.0")
    app.state.runtime = runtime or build_default_runtime()
    _configure_optional_api_key_auth(app)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "runtime-api"}

    @app.post("/agent-runs", response_model=AgentRunResponse, status_code=status.HTTP_201_CREATED)
    async def start_run(
        request: Request,
        run_request: StartRunRequest,
        tenant_id: TenantIdHeader,
    ) -> AgentRunResponse:
        runtime_service = _runtime_from_request(request)
        try:
            run = await runtime_service.start_run(
                tenant_id=tenant_id,
                user_id=run_request.user_id,
                agent_id=run_request.agent_id,
                agent_version=run_request.agent_version,
                input_payload=run_request.input,
            )
        except RuntimePolicyDeniedError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "policy_denied",
                    "message": str(exc),
                    "run_id": str(exc.run.run_id),
                    "policy_decision_id": str(exc.decision.decision_id),
                    "reason": exc.decision.reason,
                },
            ) from exc
        except RuntimeExecutionFailedError as exc:
            status_code = (
                status.HTTP_429_TOO_MANY_REQUESTS
                if exc.error_code == "budget_exceeded"
                else status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            raise HTTPException(
                status_code=status_code,
                detail={
                    "code": exc.error_code,
                    "message": str(exc),
                    "run_id": str(exc.run.run_id),
                },
            ) from exc
        return AgentRunResponse(run=run)

    @app.get("/agent-runs", response_model=AgentRunListResponse)
    def list_runs(request: Request, tenant_id: TenantIdHeader) -> AgentRunListResponse:
        runtime_service = _runtime_from_request(request)
        return AgentRunListResponse(runs=runtime_service.list_runs(tenant_id))

    @app.get("/metrics")
    def get_metrics(request: Request, tenant_id: TenantIdHeader) -> dict:
        runtime_service = _runtime_from_request(request)
        return runtime_service.metrics(tenant_id).model_dump(mode="json")

    @app.get("/agent-runs/{run_id}", response_model=AgentRunResponse)
    def get_run(request: Request, run_id: UUID, tenant_id: TenantIdHeader) -> AgentRunResponse:
        runtime_service = _runtime_from_request(request)
        try:
            return AgentRunResponse(run=runtime_service.get_run(tenant_id, run_id))
        except AgentRunNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return app


def _runtime_from_request(request: Request) -> RuntimeExecutionService:
    return request.app.state.runtime



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
