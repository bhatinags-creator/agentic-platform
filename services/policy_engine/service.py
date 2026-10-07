from typing import Any

from platform_common.domain.models import PolicyDecision


class PolicyEngineService:
    def __init__(self, allow_client_decision_override: bool = False) -> None:
        self.allow_client_decision_override = allow_client_decision_override

    async def evaluate(
        self,
        action: str,
        subject: dict[str, Any],
        resource: dict[str, Any],
    ) -> PolicyDecision:
        input_payload = resource.get("input", {})
        if (
            self.allow_client_decision_override
            and input_payload.get("policy_decision") == "deny"
        ):
            return PolicyDecision(
                decision="deny",
                reason=f"MVP policy denied action: {action}",
                constraints={"matched_rule": "input.policy_decision=deny"},
            )

        return PolicyDecision(decision="permit", reason=f"MVP policy permitted action: {action}")
