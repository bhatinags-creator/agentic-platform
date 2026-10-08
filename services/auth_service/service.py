from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    subject: str
    tenant_id: str
    roles: frozenset[Role]


class AuthenticationError(Exception):
    """Raised when a request cannot be authenticated."""


class AuthorizationError(Exception):
    """Raised when an authenticated principal lacks a required role."""


class APIKeyAuthService:
    def __init__(self, api_keys: dict[str, AuthenticatedPrincipal] | None = None) -> None:
        self.api_keys = api_keys or {}

    def authenticate(self, api_key: str | None) -> AuthenticatedPrincipal:
        if not api_key:
            raise AuthenticationError("Missing API key")
        principal = self.api_keys.get(api_key)
        if principal is None:
            raise AuthenticationError("Invalid API key")
        return principal

    @staticmethod
    def require_role(principal: AuthenticatedPrincipal, required_role: Role | str) -> None:
        resolved_role = Role(required_role)
        if resolved_role not in principal.roles and Role.ADMIN not in principal.roles:
            raise AuthorizationError(f"Required role missing: {resolved_role}")
