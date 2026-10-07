from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

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


class ToolDefinition(BaseModel):
    tool_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str | None = None
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


class ToolRegistryService:
    def __init__(self) -> None:
        self._tools: dict[tuple[str, str], ToolDefinition] = {}

    def register_tool(
        self,
        *,
        tenant_id: str,
        name: str,
        description: str | None = None,
        risk_class: ToolRiskClass | str = ToolRiskClass.MEDIUM,
        allowed_agents: list[str] | None = None,
        allowed_actions: list[str] | None = None,
        timeout_seconds: int = 30,
    ) -> ToolDefinition:
        tool = ToolDefinition(
            tenant_id=tenant_id,
            name=name,
            description=description,
            risk_class=ToolRiskClass(risk_class),
            allowed_agents=allowed_agents or [],
            allowed_actions=allowed_actions or [],
            timeout_seconds=timeout_seconds,
        )
        self._tools[(tenant_id, name)] = tool
        return tool

    def get_tool(self, tenant_id: str, name: str) -> ToolDefinition:
        tool = self._tools.get((tenant_id, name)) or self._tools.get(("default", name))
        if tool is None:
            raise ToolNotFoundError(f"Tool not found: {name}")
        return tool

    def list_tools(self, tenant_id: str) -> list[ToolDefinition]:
        return sorted(
            [
                tool
                for tool in self._tools.values()
                if tool.tenant_id in {tenant_id, "default"}
            ],
            key=lambda tool: tool.created_at,
        )

    def deprecate_tool(self, tenant_id: str, name: str) -> ToolDefinition:
        tool = self.get_tool(tenant_id, name)
        updated = tool.model_copy(update={"status": ToolStatus.DEPRECATED})
        self._tools[(tool.tenant_id, tool.name)] = updated
        return updated


class ToolGatewayService:
    def __init__(self, registry: ToolRegistryService | None = None) -> None:
        self.registry = registry or ToolRegistryService()
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

        record = self._record_invocation(
            tenant_id=tenant_id,
            tool_name=tool_ref,
            agent_id=agent_id,
            trace_id=trace_id,
            run_id=run_id,
            status=ToolInvocationStatus.SUCCEEDED,
            decision=decision,
        )
        return {
            "tool_ref": tool_ref,
            "status": record.status,
            "output": {"echo": payload},
            "audit_required": True,
            "invocation_id": str(record.invocation_id),
            "risk_class": tool.risk_class,
        }

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
                risk_class=ToolRiskClass.LOW,
            )
