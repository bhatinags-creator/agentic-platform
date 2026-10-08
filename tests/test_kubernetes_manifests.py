from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_kubernetes_manifests_include_probes_resources_and_security_contexts() -> None:
    manifest_text = "\n".join(
        [
            (ROOT / "infrastructure/kubernetes/control-plane-api.yaml").read_text(),
            (ROOT / "infrastructure/kubernetes/runtime-api.yaml").read_text(),
        ]
    )

    for expected in [
        "readinessProbe",
        "livenessProbe",
        "resources",
        "runAsNonRoot",
        "allowPrivilegeEscalation",
        "AGENTIC_PLATFORM_API_KEY",
    ]:
        assert expected in manifest_text
