from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DeploymentEnvironment(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    TEST = "test"
    PROD = "prod"


class DeploymentStatus(StrEnum):
    CREATED = "created"
    BLOCKED = "blocked"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"


class DeploymentGateType(StrEnum):
    POLICY = "policy"
    EVALUATION = "evaluation"
    RESPONSIBLE_AI = "responsible_ai"
    AISECOPS = "aisecops"


class DeploymentGateStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not_run"


class DeploymentTarget(BaseModel):
    target_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    environment: DeploymentEnvironment
    runtime_url: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeploymentGateResult(BaseModel):
    gate_type: DeploymentGateType
    status: DeploymentGateStatus
    reason: str
    evidence: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DeploymentRecord(BaseModel):
    deployment_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    agent_version_id: str = Field(min_length=1)
    target_id: UUID
    environment: DeploymentEnvironment
    status: DeploymentStatus = DeploymentStatus.CREATED
    gates: list[DeploymentGateResult] = Field(default_factory=list)
    rollback_of: UUID | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deployed_at: datetime | None = None


class DeploymentNotFoundError(Exception):
    """Raised when a deployment is not visible to the requested tenant."""


class DeploymentTargetNotFoundError(Exception):
    """Raised when a deployment target is not visible to the requested tenant."""


class DeploymentBlockedError(Exception):
    """Raised when deployment gates block a deployment."""

    def __init__(self, message: str, deployment: DeploymentRecord) -> None:
        super().__init__(message)
        self.deployment = deployment


class DeploymentService:
    def __init__(self) -> None:
        self._targets: dict[UUID, DeploymentTarget] = {}
        self._deployments: dict[UUID, DeploymentRecord] = {}

    def register_target(
        self,
        *,
        tenant_id: str,
        name: str,
        environment: DeploymentEnvironment | str,
        runtime_url: str | None = None,
    ) -> DeploymentTarget:
        target = DeploymentTarget(
            tenant_id=tenant_id,
            name=name,
            environment=DeploymentEnvironment(environment),
            runtime_url=runtime_url,
        )
        self._targets[target.target_id] = target
        return target

    def create_bundle(self, agent_version_id: str, environment: str) -> dict:
        return {
            "deployment_id": f"dep-{agent_version_id}-{environment}",
            "status": DeploymentStatus.CREATED,
        }

    def create_deployment(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        agent_version_id: str,
        target_id: UUID | str,
    ) -> DeploymentRecord:
        target = self.get_target(tenant_id, target_id)
        deployment = DeploymentRecord(
            tenant_id=tenant_id,
            agent_id=agent_id,
            agent_version_id=agent_version_id,
            target_id=target.target_id,
            environment=target.environment,
        )
        self._deployments[deployment.deployment_id] = deployment
        return deployment

    def evaluate_gates(
        self,
        *,
        tenant_id: str,
        deployment_id: UUID | str,
        policy_passed: bool = True,
        evaluation_passed: bool = True,
        responsible_ai_passed: bool = True,
        aisecops_passed: bool = True,
    ) -> DeploymentRecord:
        deployment = self.get_deployment(tenant_id, deployment_id)
        gates = [
            self._gate(DeploymentGateType.POLICY, policy_passed, "policy gate"),
            self._gate(DeploymentGateType.EVALUATION, evaluation_passed, "evaluation gate"),
            self._gate(
                DeploymentGateType.RESPONSIBLE_AI,
                responsible_ai_passed,
                "responsible AI gate",
            ),
            self._gate(DeploymentGateType.AISECOPS, aisecops_passed, "AISecOps gate"),
        ]
        status = (
            DeploymentStatus.CREATED
            if all(gate.status == DeploymentGateStatus.PASSED for gate in gates)
            else DeploymentStatus.BLOCKED
        )
        updated = deployment.model_copy(update={"gates": gates, "status": status})
        self._deployments[updated.deployment_id] = updated
        return updated

    def deploy(self, tenant_id: str, deployment_id: UUID | str) -> DeploymentRecord:
        deployment = self.get_deployment(tenant_id, deployment_id)
        if not deployment.gates:
            deployment = self.evaluate_gates(tenant_id=tenant_id, deployment_id=deployment_id)
        failed_gates = [gate for gate in deployment.gates if gate.status != DeploymentGateStatus.PASSED]
        if failed_gates:
            raise DeploymentBlockedError("Deployment gates did not pass", deployment)
        updated = deployment.model_copy(
            update={"status": DeploymentStatus.DEPLOYED, "deployed_at": datetime.now(UTC)}
        )
        self._deployments[updated.deployment_id] = updated
        return updated

    def rollback(
        self,
        *,
        tenant_id: str,
        deployment_id: UUID | str,
        target_agent_version_id: str,
    ) -> DeploymentRecord:
        deployment = self.get_deployment(tenant_id, deployment_id)
        rolled_back = deployment.model_copy(update={"status": DeploymentStatus.ROLLED_BACK})
        self._deployments[rolled_back.deployment_id] = rolled_back
        rollback = DeploymentRecord(
            tenant_id=tenant_id,
            agent_id=deployment.agent_id,
            agent_version_id=target_agent_version_id,
            target_id=deployment.target_id,
            environment=deployment.environment,
            status=DeploymentStatus.DEPLOYED,
            rollback_of=deployment.deployment_id,
            deployed_at=datetime.now(UTC),
        )
        self._deployments[rollback.deployment_id] = rollback
        return rollback

    def get_target(self, tenant_id: str, target_id: UUID | str) -> DeploymentTarget:
        target_uuid = self._parse_uuid(target_id)
        target = self._targets.get(target_uuid)
        if target is None or target.tenant_id != tenant_id:
            raise DeploymentTargetNotFoundError(f"Deployment target not found: {target_id}")
        return target

    def get_deployment(self, tenant_id: str, deployment_id: UUID | str) -> DeploymentRecord:
        deployment_uuid = self._parse_uuid(deployment_id)
        deployment = self._deployments.get(deployment_uuid)
        if deployment is None or deployment.tenant_id != tenant_id:
            raise DeploymentNotFoundError(f"Deployment not found: {deployment_id}")
        return deployment

    def list_deployments(self, tenant_id: str) -> list[DeploymentRecord]:
        return sorted(
            [deployment for deployment in self._deployments.values() if deployment.tenant_id == tenant_id],
            key=lambda deployment: deployment.created_at,
        )

    @staticmethod
    def _gate(
        gate_type: DeploymentGateType,
        passed: bool,
        label: str,
    ) -> DeploymentGateResult:
        return DeploymentGateResult(
            gate_type=gate_type,
            status=DeploymentGateStatus.PASSED if passed else DeploymentGateStatus.FAILED,
            reason=f"{label} {'passed' if passed else 'failed'}",
        )

    @staticmethod
    def _parse_uuid(value: UUID | str) -> UUID:
        if isinstance(value, UUID):
            return value
        return UUID(value)
