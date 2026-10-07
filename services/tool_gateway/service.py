from typing import Any


class ToolGatewayService:
    async def invoke(self, tool_ref: str, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {"tool_ref": tool_ref, "status": "succeeded", "output": {"echo": payload}, "audit_required": True}
