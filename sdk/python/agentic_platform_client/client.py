from __future__ import annotations

from typing import Any

import httpx


class AgenticPlatformClient:
    def __init__(self, control_plane_url: str, runtime_url: str, tenant_id: str = "default") -> None:
        self.control_plane_url = control_plane_url.rstrip("/")
        self.runtime_url = runtime_url.rstrip("/")
        self.tenant_id = tenant_id

    @property
    def _headers(self) -> dict[str, str]:
        return {"X-Tenant-ID": self.tenant_id}

    async def create_agent(self, *, name: str, owner: str, risk_class: str = "medium") -> dict[str, Any]:
        payload = {"name": name, "owner": owner, "risk_class": risk_class}
        return await self._post(f"{self.control_plane_url}/agents", payload)

    async def list_agents(self) -> dict[str, Any]:
        return await self._get(f"{self.control_plane_url}/agents")

    async def get_agent(self, agent_id: str) -> dict[str, Any]:
        return await self._get(f"{self.control_plane_url}/agents/{agent_id}")

    async def publish_agent_version(self, agent_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{self.control_plane_url}/agents/{agent_id}/versions", {"manifest": manifest})

    async def list_agent_versions(self, agent_id: str) -> dict[str, Any]:
        return await self._get(f"{self.control_plane_url}/agents/{agent_id}/versions")

    async def create_agent_draft(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{self.control_plane_url}/studio/agent-drafts", payload)

    async def list_agent_drafts(self) -> dict[str, Any]:
        return await self._get(f"{self.control_plane_url}/studio/agent-drafts")

    async def start_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._post(f"{self.runtime_url}/agent-runs", payload)

    async def list_runs(self) -> dict[str, Any]:
        return await self._get(f"{self.runtime_url}/agent-runs")

    async def get_run(self, run_id: str) -> dict[str, Any]:
        return await self._get(f"{self.runtime_url}/agent-runs/{run_id}")

    async def get_metrics(self) -> dict[str, Any]:
        return await self._get(f"{self.runtime_url}/metrics")

    async def _get(self, url: str) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers)
            response.raise_for_status()
            return response.json()

    async def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self._headers)
            response.raise_for_status()
            return response.json()
