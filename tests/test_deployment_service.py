import pytest

from services.deployment_service.service import (
    DeploymentBlockedError,
    DeploymentEnvironment,
    DeploymentService,
    DeploymentStatus,
)


def test_deployment_service_deploys_when_gates_pass() -> None:
    service = DeploymentService()
    target = service.register_target(
        tenant_id="tenant-a",
        name="local-runtime",
        environment=DeploymentEnvironment.LOCAL,
    )
    deployment = service.create_deployment(
        tenant_id="tenant-a",
        agent_id="agent.support",
        agent_version_id="version-1",
        target_id=target.target_id,
    )

    evaluated = service.evaluate_gates(tenant_id="tenant-a", deployment_id=deployment.deployment_id)
    deployed = service.deploy("tenant-a", evaluated.deployment_id)

    assert deployed.status == DeploymentStatus.DEPLOYED
    assert deployed.deployed_at is not None
    assert len(deployed.gates) == 4


def test_deployment_service_blocks_failed_gate_and_can_rollback() -> None:
    service = DeploymentService()
    target = service.register_target(tenant_id="tenant-a", name="prod", environment="prod")
    deployment = service.create_deployment(
        tenant_id="tenant-a",
        agent_id="agent.support",
        agent_version_id="version-2",
        target_id=target.target_id,
    )
    blocked = service.evaluate_gates(
        tenant_id="tenant-a",
        deployment_id=deployment.deployment_id,
        evaluation_passed=False,
    )

    with pytest.raises(DeploymentBlockedError):
        service.deploy("tenant-a", blocked.deployment_id)

    deployed = service.evaluate_gates(tenant_id="tenant-a", deployment_id=blocked.deployment_id)
    deployed = service.deploy("tenant-a", deployed.deployment_id)
    rollback = service.rollback(
        tenant_id="tenant-a",
        deployment_id=deployed.deployment_id,
        target_agent_version_id="version-1",
    )

    assert rollback.status == DeploymentStatus.DEPLOYED
    assert rollback.rollback_of == deployed.deployment_id
    assert service.get_deployment("tenant-a", deployed.deployment_id).status == DeploymentStatus.ROLLED_BACK
