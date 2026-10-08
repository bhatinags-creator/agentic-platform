from services.auth_service.service import (
    APIKeyAuthService,
    AuthenticatedPrincipal,
    AuthenticationError,
    AuthorizationError,
    Role,
)


def test_api_key_auth_service_authenticates_principal() -> None:
    principal = AuthenticatedPrincipal(
        subject="user-1",
        tenant_id="tenant-a",
        roles=frozenset({Role.DEVELOPER}),
    )
    service = APIKeyAuthService(api_keys={"secret": principal})

    authenticated = service.authenticate("secret")

    assert authenticated == principal


def test_api_key_auth_service_rejects_missing_or_unknown_key() -> None:
    service = APIKeyAuthService(api_keys={})

    try:
        service.authenticate(None)
    except AuthenticationError as exc:
        assert "Missing" in str(exc)
    else:
        raise AssertionError("missing API key should fail")

    try:
        service.authenticate("wrong")
    except AuthenticationError as exc:
        assert "Invalid" in str(exc)
    else:
        raise AssertionError("unknown API key should fail")


def test_require_role_allows_admin_override_and_rejects_missing_role() -> None:
    admin = AuthenticatedPrincipal(
        subject="admin",
        tenant_id="tenant-a",
        roles=frozenset({Role.ADMIN}),
    )
    viewer = AuthenticatedPrincipal(
        subject="viewer",
        tenant_id="tenant-a",
        roles=frozenset({Role.VIEWER}),
    )

    APIKeyAuthService.require_role(admin, Role.DEVELOPER)

    try:
        APIKeyAuthService.require_role(viewer, Role.DEVELOPER)
    except AuthorizationError as exc:
        assert "developer" in str(exc)
    else:
        raise AssertionError("viewer should not satisfy developer role")
