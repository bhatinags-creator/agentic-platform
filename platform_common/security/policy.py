from typing import Any

from platform_common.domain.models import PolicyDecision


class PolicyClient:
    def evaluate(self, action: str, subject: dict[str, Any], resource: dict[str, Any]) -> PolicyDecision:
        return PolicyDecision(decision="permit", reason=f"MVP permit for {action}")
