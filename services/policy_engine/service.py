from typing import Any

from platform_common.domain.models import PolicyDecision


class PolicyEngineService:
    async def evaluate(
        self,
        action: str,
        subject: dict[str, Any],
        resource: dict[str, Any],
    ) -> PolicyDecision:
        input_payload = resource.get("input", {})
        if input_payload.get("policy_decision") == "deny":
            return PolicyDecision(
                decision="deny",
                reason=f"MVP policy denied action: {action}",
                constraints={"matched_rule": "input.policy_decision=deny"},
            )

        return PolicyDecision(decision="permit", reason=f"MVP policy permitted action: {action}")
