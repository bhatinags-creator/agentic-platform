import json

import httpx
import pytest

from services.tool_gateway.service import (
    ToolGatewayService,
    ToolImplementationType,
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
        implementation_type=ToolImplementationType.ECHO,
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
async def test_tool_gateway_invokes_rest_tool_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.example.test/weather"
        assert request.method == "POST"
        assert json.loads(request.content) == {"latitude": 28.6, "longitude": 77.2}
        return httpx.Response(200, json={"temperature": 31, "condition": "clear"})

    registry = ToolRegistryService()
    registry.register_tool(
        tenant_id="tenant-a",
        name="get_current_weather",
        implementation_type=ToolImplementationType.REST,
        endpoint_url="https://api.example.test/weather",
        method="POST",
        allowed_actions=["read"],
    )
    transport = httpx.MockTransport(handler)
    gateway = ToolGatewayService(
        registry=registry,
        http_client_factory=lambda: httpx.AsyncClient(transport=transport),
    )

    result = await gateway.invoke(
        "get_current_weather",
        {"action": "read", "latitude": 28.6, "longitude": 77.2},
        {"tenant_id": "tenant-a", "agent_id": "agent.weather"},
    )

    assert result["status"] == ToolInvocationStatus.SUCCEEDED
    assert result["output"]["http_status"] == 200
    assert result["output"]["body"] == {"temperature": 31, "condition": "clear"}


@pytest.mark.anyio
async def test_tool_gateway_invokes_website_tool_on_configured_domain() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://www.aubank.in/personal-banking/current-account"
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            text="<html><body>AU current account product information</body></html>",
        )

    registry = ToolRegistryService()
    registry.register_tool(
        tenant_id="tenant-a",
        name="au.website",
        implementation_type=ToolImplementationType.WEBSITE,
        endpoint_url="https://www.aubank.in",
        allowed_actions=["read"],
    )
    transport = httpx.MockTransport(handler)
    gateway = ToolGatewayService(
        registry=registry,
        http_client_factory=lambda: httpx.AsyncClient(transport=transport),
    )

    result = await gateway.invoke(
        "au.website",
        {"action": "read", "path": "/personal-banking/current-account"},
        {"tenant_id": "tenant-a", "agent_id": "agent.product-advisor"},
    )

    assert result["status"] == ToolInvocationStatus.SUCCEEDED
    assert result["output"]["http_status"] == 200
    assert "AU current account product information" in result["output"]["text"]


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
