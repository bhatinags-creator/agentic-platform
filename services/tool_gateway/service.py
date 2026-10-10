from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import closing
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import UUID, uuid4

import httpx
from pydantic import BaseModel, Field


class ToolRiskClass(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolStatus(StrEnum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class ToolInvocationStatus(StrEnum):
    SUCCEEDED = "succeeded"
    DENIED = "denied"
    FAILED = "failed"


class ToolImplementationType(StrEnum):
    REST = "rest"
    OPENAPI = "openapi"
    WEBSITE = "website"
    MCP = "mcp"
    PYTHON = "python"
    ECHO = "echo"


class ToolDefinition(BaseModel):
    tool_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
    implementation_type: ToolImplementationType = ToolImplementationType.REST
    endpoint_url: str | None = None
    method: str = "POST"
    auth_type: str = "none"
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    risk_class: ToolRiskClass = ToolRiskClass.MEDIUM
    allowed_agents: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=30, ge=1)
    status: ToolStatus = ToolStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolInvocationDecision(BaseModel):
    permitted: bool
    reason: str
    constraints: dict[str, Any] = Field(default_factory=dict)


class ToolInvocationRecord(BaseModel):
    invocation_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    trace_id: str | None = None
    run_id: str | None = None
    status: ToolInvocationStatus
    decision: ToolInvocationDecision
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ToolNotFoundError(Exception):
    """Raised when a tool is not registered or not visible to the tenant."""


class ToolInvocationDeniedError(Exception):
    """Raised when tool governance denies an invocation."""

    def __init__(self, message: str, record: ToolInvocationRecord) -> None:
        super().__init__(message)
        self.record = record


class ToolInvocationExecutionError(Exception):
    """Raised when a permitted tool invocation fails during execution."""


class ToolRepository(ABC):
    @abstractmethod
    def save_tool(self, tool: ToolDefinition) -> ToolDefinition:
        raise NotImplementedError

    @abstractmethod
    def get_tool(self, tenant_id: str, name: str) -> ToolDefinition | None:
        raise NotImplementedError

    @abstractmethod
    def list_tools(self, tenant_id: str) -> list[ToolDefinition]:
        raise NotImplementedError


class InMemoryToolRepository(ToolRepository):
    def __init__(self) -> None:
        self._tools: dict[tuple[str, str], ToolDefinition] = {}

    def save_tool(self, tool: ToolDefinition) -> ToolDefinition:
        self._tools[(tool.tenant_id, tool.name)] = tool
        return tool

    def get_tool(self, tenant_id: str, name: str) -> ToolDefinition | None:
        return self._tools.get((tenant_id, name)) or self._tools.get(("default", name))

    def list_tools(self, tenant_id: str) -> list[ToolDefinition]:
        return sorted(
            [tool for tool in self._tools.values() if tool.tenant_id in {tenant_id, "default"}],
            key=lambda tool: tool.created_at,
        )


class SQLiteToolRepository(ToolRepository):
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save_tool(self, tool: ToolDefinition) -> ToolDefinition:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO tools (
                    tool_id, tenant_id, name, risk_class, status, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tenant_id, name) DO UPDATE SET
                    risk_class = excluded.risk_class,
                    status = excluded.status,
                    payload_json = excluded.payload_json
                """,
                (
                    str(tool.tool_id),
                    tool.tenant_id,
                    tool.name,
                    tool.risk_class.value,
                    tool.status.value,
                    tool.created_at.isoformat(),
                    tool.model_dump_json(),
                ),
            )
        return tool

    def get_tool(self, tenant_id: str, name: str) -> ToolDefinition | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT payload_json FROM tools
                WHERE (tenant_id = ? OR tenant_id = 'default') AND name = ?
                ORDER BY CASE WHEN tenant_id = ? THEN 0 ELSE 1 END
                LIMIT 1
                """,
                (tenant_id, name, tenant_id),
            ).fetchone()
        return self._tool_from_row(row)

    def list_tools(self, tenant_id: str) -> list[ToolDefinition]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM tools
                WHERE tenant_id IN (?, 'default')
                ORDER BY created_at ASC
                """,
                (tenant_id,),
            ).fetchall()
        return [ToolDefinition.model_validate_json(row["payload_json"]) for row in rows]

    def _initialize_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tools (
                    tool_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    risk_class TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE (tenant_id, name)
                );
                CREATE INDEX IF NOT EXISTS idx_tools_tenant_created
                    ON tools (tenant_id, created_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _tool_from_row(row: sqlite3.Row | None) -> ToolDefinition | None:
        if row is None:
            return None
        return ToolDefinition.model_validate_json(row["payload_json"])


class ToolRegistryService:
    def __init__(self, repository: ToolRepository | None = None) -> None:
        self.repository = repository or InMemoryToolRepository()

    def register_tool(
        self,
        *,
        tenant_id: str,
        name: str,
        description: str | None = None,
        implementation_type: ToolImplementationType | str = ToolImplementationType.REST,
        endpoint_url: str | None = None,
        method: str = "POST",
        auth_type: str = "none",
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        risk_class: ToolRiskClass | str = ToolRiskClass.MEDIUM,
        allowed_agents: list[str] | None = None,
        allowed_actions: list[str] | None = None,
        timeout_seconds: int = 30,
    ) -> ToolDefinition:
        tool = ToolDefinition(
            tenant_id=tenant_id,
            name=name,
            description=description,
            implementation_type=ToolImplementationType(implementation_type),
            endpoint_url=endpoint_url,
            method=method.upper(),
            auth_type=auth_type,
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            risk_class=ToolRiskClass(risk_class),
            allowed_agents=allowed_agents or [],
            allowed_actions=allowed_actions or [],
            timeout_seconds=timeout_seconds,
        )
        return self.repository.save_tool(tool)

    def get_tool(self, tenant_id: str, name: str) -> ToolDefinition:
        tool = self.repository.get_tool(tenant_id, name)
        if tool is None:
            raise ToolNotFoundError(f"Tool not found: {name}")
        return tool

    def list_tools(self, tenant_id: str) -> list[ToolDefinition]:
        return self.repository.list_tools(tenant_id)

    def deprecate_tool(self, tenant_id: str, name: str) -> ToolDefinition:
        tool = self.get_tool(tenant_id, name)
        updated = tool.model_copy(update={"status": ToolStatus.DEPRECATED})
        return self.repository.save_tool(updated)


class ToolGatewayService:
    def __init__(
        self,
        registry: ToolRegistryService | None = None,
        http_client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        self.registry = registry or ToolRegistryService()
        self.http_client_factory = http_client_factory or httpx.AsyncClient
        self.invocations: list[ToolInvocationRecord] = []
        self._ensure_default_tools()

    async def invoke(
        self,
        tool_ref: str,
        payload: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        tenant_id = context.get("tenant_id", "default")
        agent_id = context.get("agent_id", "unknown")
        trace_id = context.get("trace_id")
        run_id = context.get("run_id")
        tool = self.registry.get_tool(tenant_id, tool_ref)
        decision = self.evaluate_invocation(tool, agent_id=agent_id, payload=payload)
        if not decision.permitted:
            record = self._record_invocation(
                tenant_id=tenant_id,
                tool_name=tool_ref,
                agent_id=agent_id,
                trace_id=trace_id,
                run_id=run_id,
                status=ToolInvocationStatus.DENIED,
                decision=decision,
            )
            raise ToolInvocationDeniedError(decision.reason, record)

        try:
            output = await self._execute_tool(tool, payload)
            status_value = ToolInvocationStatus.SUCCEEDED
        except ToolInvocationExecutionError:
            record = self._record_invocation(
                tenant_id=tenant_id,
                tool_name=tool_ref,
                agent_id=agent_id,
                trace_id=trace_id,
                run_id=run_id,
                status=ToolInvocationStatus.FAILED,
                decision=decision,
            )
            raise

        record = self._record_invocation(
            tenant_id=tenant_id,
            tool_name=tool_ref,
            agent_id=agent_id,
            trace_id=trace_id,
            run_id=run_id,
            status=status_value,
            decision=decision,
        )
        return {
            "tool_ref": tool_ref,
            "status": record.status,
            "output": output,
            "audit_required": True,
            "invocation_id": str(record.invocation_id),
            "risk_class": tool.risk_class,
        }

    async def _execute_tool(
        self,
        tool: ToolDefinition,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if tool.implementation_type == ToolImplementationType.ECHO:
            return {"echo": payload}
        if tool.implementation_type in {ToolImplementationType.REST, ToolImplementationType.OPENAPI}:
            return await self._invoke_rest_tool(tool, payload)
        if tool.implementation_type == ToolImplementationType.WEBSITE:
            return await self._invoke_website_tool(tool, payload)
        raise ToolInvocationExecutionError(
            f"Tool implementation type is not executable yet: {tool.implementation_type}"
        )

    async def _invoke_rest_tool(
        self,
        tool: ToolDefinition,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not tool.endpoint_url:
            raise ToolInvocationExecutionError("REST tool endpoint_url is required.")

        request_payload = {key: value for key, value in payload.items() if key != "action"}
        method = tool.method.upper()
        request_kwargs: dict[str, Any] = {"timeout": tool.timeout_seconds}
        if method == "GET":
            request_kwargs["params"] = request_payload
        elif method in {"POST", "PUT", "PATCH", "DELETE"}:
            request_kwargs["json"] = request_payload
        else:
            raise ToolInvocationExecutionError(f"Unsupported REST tool method: {tool.method}")

        try:
            async with self.http_client_factory() as client:
                response = await client.request(method, tool.endpoint_url, **request_kwargs)
        except httpx.HTTPError as exc:
            raise ToolInvocationExecutionError(f"REST tool invocation failed: {exc}") from exc

        try:
            body: Any = response.json()
        except ValueError:
            body = response.text

        return {
            "http_status": response.status_code,
            "headers": {
                key: value
                for key, value in response.headers.items()
                if key.lower() in {"content-type", "content-length"}
            },
            "body": body,
        }

    async def _invoke_website_tool(
        self,
        tool: ToolDefinition,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not tool.endpoint_url:
            raise ToolInvocationExecutionError("Website tool endpoint_url is required.")

        target_url = self._website_target_url(tool.endpoint_url, payload)
        try:
            async with self.http_client_factory() as client:
                response = await client.get(
                    target_url,
                    timeout=tool.timeout_seconds,
                    follow_redirects=True,
                    headers={"User-Agent": "AgenticPlatformToolGateway/0.1"},
                )
        except httpx.HTTPError as exc:
            raise ToolInvocationExecutionError(f"Website tool retrieval failed: {exc}") from exc

        text = response.text
        max_chars = int(payload.get("max_chars") or 12000)
        return {
            "http_status": response.status_code,
            "url": str(response.url),
            "content_type": response.headers.get("content-type"),
            "text": text[:max_chars],
            "truncated": len(text) > max_chars,
        }

    @staticmethod
    def _website_target_url(endpoint_url: str, payload: dict[str, Any]) -> str:
        base = endpoint_url.rstrip("/") + "/"
        requested_url = str(payload.get("url") or "").strip()
        path = str(payload.get("path") or "").strip()
        target = requested_url or urljoin(base, path.lstrip("/"))
        base_parts = urlparse(base)
        target_parts = urlparse(target)
        if target_parts.scheme not in {"http", "https"}:
            raise ToolInvocationExecutionError("Website tool URL must be http or https.")
        if target_parts.netloc.lower() != base_parts.netloc.lower():
            raise ToolInvocationExecutionError("Website tool URL must stay on the configured domain.")
        return target

    def evaluate_invocation(
        self,
        tool: ToolDefinition,
        *,
        agent_id: str,
        payload: dict[str, Any],
    ) -> ToolInvocationDecision:
        if tool.status != ToolStatus.ACTIVE:
            return ToolInvocationDecision(permitted=False, reason="tool is not active")
        if tool.allowed_agents and agent_id not in tool.allowed_agents:
            return ToolInvocationDecision(
                permitted=False,
                reason="agent is not allowed to invoke this tool",
                constraints={"allowed_agents": tool.allowed_agents},
            )
        action = payload.get("action")
        if tool.allowed_actions and action not in tool.allowed_actions:
            return ToolInvocationDecision(
                permitted=False,
                reason="action is not allowed for this tool",
                constraints={"allowed_actions": tool.allowed_actions},
            )
        return ToolInvocationDecision(permitted=True, reason="tool invocation permitted")

    def list_invocations(self, tenant_id: str, agent_id: str | None = None) -> list[ToolInvocationRecord]:
        return [
            invocation
            for invocation in self.invocations
            if invocation.tenant_id == tenant_id
            and (agent_id is None or invocation.agent_id == agent_id)
        ]

    def _record_invocation(
        self,
        *,
        tenant_id: str,
        tool_name: str,
        agent_id: str,
        trace_id: str | None,
        run_id: str | None,
        status: ToolInvocationStatus,
        decision: ToolInvocationDecision,
    ) -> ToolInvocationRecord:
        record = ToolInvocationRecord(
            tenant_id=tenant_id,
            tool_name=tool_name,
            agent_id=agent_id,
            trace_id=trace_id,
            run_id=run_id,
            status=status,
            decision=decision,
        )
        self.invocations.append(record)
        return record

    def _ensure_default_tools(self) -> None:
        try:
            self.registry.get_tool("default", "mvp.echo")
        except ToolNotFoundError:
            self.registry.register_tool(
                tenant_id="default",
                name="mvp.echo",
                description="MVP echo tool used by the runtime smoke path.",
                implementation_type=ToolImplementationType.ECHO,
                risk_class=ToolRiskClass.LOW,
            )
