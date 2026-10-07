from protocols.mcp.service import (
    MCPAdapterRegistry,
    MCPResourceReference,
    MCPServerNotFoundError,
    MCPToolReference,
    StaticMCPAdapter,
)


def test_mcp_adapter_registry_lists_server_tools_and_resources() -> None:
    registry = MCPAdapterRegistry()
    server = registry.register_server(
        tenant_id="tenant-a",
        name="local-tools",
        endpoint="stdio://local-tools",
    )
    registry.adapter = StaticMCPAdapter(
        tools=[MCPToolReference(server_id=server.server_id, name="search")],
        resources=[MCPResourceReference(server_id=server.server_id, uri="file://kb.md")],
    )

    assert registry.list_servers("tenant-a") == [server]
    assert registry.list_server_tools("tenant-a", server.server_id)[0].name == "search"
    assert registry.list_server_resources("tenant-a", server.server_id)[0].uri == "file://kb.md"


def test_mcp_server_lookup_is_tenant_scoped() -> None:
    registry = MCPAdapterRegistry()
    server = registry.register_server(
        tenant_id="tenant-a",
        name="local-tools",
        endpoint="stdio://local-tools",
    )

    try:
        registry.get_server("tenant-b", server.server_id)
    except MCPServerNotFoundError as exc:
        assert str(server.server_id) in str(exc)
    else:
        raise AssertionError("Expected MCPServerNotFoundError")
