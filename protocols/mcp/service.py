from __future__ import annotations

from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MCPServerStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class MCPServerDefinition(BaseModel):
    server_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    status: MCPServerStatus = MCPServerStatus.ACTIVE
    metadata: dict = Field(default_factory=dict)


class MCPToolReference(BaseModel):
    server_id: UUID
    name: str = Field(min_length=1)
    description: str | None = None
    input_schema: dict = Field(default_factory=dict)


class MCPResourceReference(BaseModel):
    server_id: UUID
    uri: str = Field(min_length=1)
    description: str | None = None
    metadata: dict = Field(default_factory=dict)


class MCPAdapter(Protocol):
    def list_tools(self, server: MCPServerDefinition) -> list[MCPToolReference]:
        raise NotImplementedError

    def list_resources(self, server: MCPServerDefinition) -> list[MCPResourceReference]:
        raise NotImplementedError


class StaticMCPAdapter:
    def __init__(
        self,
        tools: list[MCPToolReference] | None = None,
        resources: list[MCPResourceReference] | None = None,
    ) -> None:
        self.tools = tools or []
        self.resources = resources or []

    def list_tools(self, server: MCPServerDefinition) -> list[MCPToolReference]:
        return [tool for tool in self.tools if tool.server_id == server.server_id]

    def list_resources(self, server: MCPServerDefinition) -> list[MCPResourceReference]:
        return [resource for resource in self.resources if resource.server_id == server.server_id]


class MCPServerNotFoundError(Exception):
    """Raised when an MCP server is not visible to the requested tenant."""


class MCPAdapterRegistry:
    def __init__(self, adapter: MCPAdapter | None = None) -> None:
        self.adapter = adapter or StaticMCPAdapter()
        self._servers: dict[UUID, MCPServerDefinition] = {}

    def register_server(
        self,
        *,
        tenant_id: str,
        name: str,
        endpoint: str,
        metadata: dict | None = None,
    ) -> MCPServerDefinition:
        server = MCPServerDefinition(
            tenant_id=tenant_id,
            name=name,
            endpoint=endpoint,
            metadata=metadata or {},
        )
        self._servers[server.server_id] = server
        return server

    def get_server(self, tenant_id: str, server_id: UUID | str) -> MCPServerDefinition:
        server_uuid = server_id if isinstance(server_id, UUID) else UUID(server_id)
        server = self._servers.get(server_uuid)
        if server is None or server.tenant_id != tenant_id:
            raise MCPServerNotFoundError(f"MCP server not found: {server_id}")
        return server

    def list_servers(self, tenant_id: str) -> list[MCPServerDefinition]:
        return sorted(
            [server for server in self._servers.values() if server.tenant_id == tenant_id],
            key=lambda server: server.name,
        )

    def list_server_tools(self, tenant_id: str, server_id: UUID | str) -> list[MCPToolReference]:
        server = self.get_server(tenant_id, server_id)
        return self.adapter.list_tools(server)

    def list_server_resources(
        self, tenant_id: str, server_id: UUID | str
    ) -> list[MCPResourceReference]:
        server = self.get_server(tenant_id, server_id)
        return self.adapter.list_resources(server)
