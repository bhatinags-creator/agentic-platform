from typing import Any


class LangGraphAdapter:
    def compile(self, canonical_workflow: dict[str, Any]) -> dict[str, Any]:
        return {"runtime": "langgraph", "compiled": canonical_workflow}
    async def execute(self, compiled_workflow: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        return {"status": "completed", "state": state, "workflow": compiled_workflow}
