import httpx


class AgenticPlatformClient:
    def __init__(self, control_plane_url: str, runtime_url: str) -> None:
        self.control_plane_url = control_plane_url.rstrip("/")
        self.runtime_url = runtime_url.rstrip("/")
    async def start_run(self, payload: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{self.runtime_url}/agent-runs", json=payload)
            response.raise_for_status()
            return response.json()
