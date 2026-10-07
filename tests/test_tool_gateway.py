import pytest

from services.tool_gateway.service import (
    ToolGatewayService,
    ToolInvocationDeniedError,
    ToolInvocationStatus,
    ToolRegistryService,
    ToolRiskClass,
    ToolStatus,
)


@pytest.mark.anyio
async def test_tool_gateway_invokes_registered_tool_and_records_invocation() -> None:
    registry = ToolRegistryService()
    registry.register_tool(
        tenant_id="tenant-a",
        name="crm.lookup",
        risk_class=ToolRiskClass.MEDIUM,
        allowed_agents=["agent.support"],
        allowed_actions=["read"],
    )
    gateway = ToolGatewayService(registry=registry)

    result = await gateway.invoke(
        "crm.lookup",
        {"action": "read", "customer_id": "123"},
        {"tenant_id": "tenant-a", "agent_id": "agent.support", "trace_id": "trace-1"},
    )

    assert result["status"] == ToolInvocationStatus.SUCCEEDED
    invocations = gateway.list_invocations("tenant-a", agent_id="agent.support")
    assert len(invocations) == 1
    assert invocations[0].decision.permitted is True


@pytest.mark.anyio
async def test_tool_gateway_denies_disallowed_agent_and_records_invocation() -> None:
    registry = ToolRegistryService()
    registry.register_tool(
        tenant_id="tenant-a",
        name="crm.delete",
        risk_class="critical",
        allowed_agents=["agent.admin"],
    )
    gateway = ToolGatewayService(registry=registry)

    with pytest.raises(ToolInvocationDeniedError) as exc_info:
        await gateway.invoke(
            "crm.delete",
            {"action": "delete"},
            {"tenant_id": "tenant-a", "agent_id": "agent.support"},
        )

    assert exc_info.value.record.status == ToolInvocationStatus.DENIED
    assert exc_info.value.record.decision.permitted is False
    assert gateway.list_invocations("tenant-a")[0].tool_name == "crm.delete"


def test_tool_registry_deprecates_tool() -> None:
    registry = ToolRegistryService()
    registry.register_tool(tenant_id="tenant-a", name="crm.lookup")

    deprecated = registry.deprecate_tool("tenant-a", "crm.lookup")

    assert deprecated.status == ToolStatus.DEPRECATED
