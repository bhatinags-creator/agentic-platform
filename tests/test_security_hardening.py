from services.security_hardening.service import SecurityHardeningService


def test_security_hardening_service_reports_header_controls() -> None:
    service = SecurityHardeningService()

    findings = service.review_runtime_headers({"X-Tenant-ID": "tenant-a"})

    assert [finding.control for finding in findings] == [
        "tenant_header_present",
        "api_key_present_when_enabled",
    ]
    assert findings[0].passed is True
    assert findings[1].passed is False


def test_security_hardening_service_accepts_authorization_header() -> None:
    service = SecurityHardeningService()

    findings = service.review_runtime_headers(
        {"X-Tenant-ID": "tenant-a", "Authorization": "Bearer token"}
    )

    assert all(finding.passed for finding in findings)
