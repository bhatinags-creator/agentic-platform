from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SecurityFinding:
    control: str
    passed: bool
    recommendation: str


class SecurityHardeningService:
    def review_runtime_headers(self, headers: dict[str, str]) -> list[SecurityFinding]:
        return [
            SecurityFinding(
                control="tenant_header_present",
                passed=bool(headers.get("X-Tenant-ID")),
                recommendation="Require tenant identity from authenticated context in production.",
            ),
            SecurityFinding(
                control="api_key_present_when_enabled",
                passed="X-API-Key" in headers or "Authorization" in headers,
                recommendation="Enable API key or bearer token authentication before production exposure.",
            ),
        ]
