from __future__ import annotations

from abc import ABC, abstractmethod
from hashlib import sha256
from uuid import UUID

from platform_common.domain.models import (
    AgentDefinition,
    AgentManifest,
    AgentVersion,
    LifecycleStatus,
    RiskClass,
)


class AgentRegistryError(Exception):
    """Base error for Agent Registry use cases."""


class AgentNotFoundError(AgentRegistryError):
    """Raised when an agent id does not exist for the requested tenant."""


class DuplicateAgentNameError(AgentRegistryError):
    """Raised when a tenant tries to create two agents with the same name."""


class DuplicateAgentVersionError(AgentRegistryError):
    """Raised when an agent already has the manifest version being published."""


class AgentRegistryRepository(ABC):
    """Storage contract used by the Agent Registry service.

    The service owns business rules. The repository owns persistence details.
    Today this project uses an in-memory repository; later this same interface can
    be backed by Postgres without changing API or workflow code.
    """

    @abstractmethod
    def save_agent(self, agent: AgentDefinition) -> AgentDefinition:
        raise NotImplementedError

    @abstractmethod
    def get_agent(self, tenant_id: str, agent_id: UUID) -> AgentDefinition | None:
        raise NotImplementedError

    @abstractmethod
    def find_agent_by_name(self, tenant_id: str, name: str) -> AgentDefinition | None:
        raise NotImplementedError

    @abstractmethod
    def list_agents(self, tenant_id: str) -> list[AgentDefinition]:
        raise NotImplementedError

    @abstractmethod
    def save_version(self, version: AgentVersion) -> AgentVersion:
        raise NotImplementedError

    @abstractmethod
    def get_version(self, tenant_id: str, version_id: UUID) -> AgentVersion | None:
        raise NotImplementedError

    @abstractmethod
    def find_version_by_manifest_version(
        self, tenant_id: str, agent_id: UUID, manifest_version: str
    ) -> AgentVersion | None:
        raise NotImplementedError

    @abstractmethod
    def list_versions(self, tenant_id: str, agent_id: UUID) -> list[AgentVersion]:
        raise NotImplementedError


class InMemoryAgentRegistryRepository(AgentRegistryRepository):
    """Development repository for local learning and unit tests."""

    def __init__(self) -> None:
        self._agents: dict[UUID, AgentDefinition] = {}
        self._versions: dict[UUID, AgentVersion] = {}

    def save_agent(self, agent: AgentDefinition) -> AgentDefinition:
        self._agents[agent.agent_id] = agent
        return agent

    def get_agent(self, tenant_id: str, agent_id: UUID) -> AgentDefinition | None:
        agent = self._agents.get(agent_id)
        if agent is None or agent.tenant_id != tenant_id:
            return None
        return agent

    def find_agent_by_name(self, tenant_id: str, name: str) -> AgentDefinition | None:
        normalized_name = name.casefold()
        return next(
            (
                agent
                for agent in self._agents.values()
                if agent.tenant_id == tenant_id and agent.name.casefold() == normalized_name
            ),
            None,
        )

    def list_agents(self, tenant_id: str) -> list[AgentDefinition]:
        return sorted(
            [agent for agent in self._agents.values() if agent.tenant_id == tenant_id],
            key=lambda agent: agent.created_at,
        )

    def save_version(self, version: AgentVersion) -> AgentVersion:
        self._versions[version.version_id] = version
        return version

    def get_version(self, tenant_id: str, version_id: UUID) -> AgentVersion | None:
        version = self._versions.get(version_id)
        if version is None:
            return None

        agent = self.get_agent(tenant_id, version.agent_id)
        if agent is None:
            return None
        return version

    def find_version_by_manifest_version(
        self, tenant_id: str, agent_id: UUID, manifest_version: str
    ) -> AgentVersion | None:
        return next(
            (
                version
                for version in self._versions.values()
                if version.agent_id == agent_id
                and version.manifest.version == manifest_version
                and self.get_agent(tenant_id, version.agent_id) is not None
            ),
            None,
        )

    def list_versions(self, tenant_id: str, agent_id: UUID) -> list[AgentVersion]:
        if self.get_agent(tenant_id, agent_id) is None:
            return []
        return sorted(
            [version for version in self._versions.values() if version.agent_id == agent_id],
            key=lambda version: version.created_at,
        )


class AgentRegistryService:
    """Coordinates agent registration, versioning, and publish lifecycle rules."""

    def __init__(self, repository: AgentRegistryRepository | None = None) -> None:
        self.repository = repository or InMemoryAgentRegistryRepository()

    def create_agent(
        self,
        tenant_id: str,
        name: str,
        owner: str,
        risk_class: RiskClass = RiskClass.MEDIUM,
    ) -> AgentDefinition:
        existing_agent = self.repository.find_agent_by_name(tenant_id, name)
        if existing_agent is not None:
            raise DuplicateAgentNameError(f"Agent name already exists for tenant: {name}")

        agent = AgentDefinition(
            tenant_id=tenant_id,
            name=name,
            owner=owner,
            risk_class=risk_class,
        )
        return self.repository.save_agent(agent)

    def get_agent(self, tenant_id: str, agent_id: UUID | str) -> AgentDefinition:
        agent_uuid = self._parse_uuid(agent_id)
        agent = self.repository.get_agent(tenant_id, agent_uuid)
        if agent is None:
            raise AgentNotFoundError(f"Agent not found: {agent_id}")
        return agent

    def list_agents(self, tenant_id: str) -> list[AgentDefinition]:
        return self.repository.list_agents(tenant_id)

    def publish_version(
        self, tenant_id: str, agent_id: UUID | str, manifest: AgentManifest
    ) -> AgentVersion:
        agent_uuid = self._parse_uuid(agent_id)
        agent = self.repository.get_agent(tenant_id, agent_uuid)
        if agent is None:
            raise AgentNotFoundError(f"Agent not found: {agent_id}")

        duplicate_version = self.repository.find_version_by_manifest_version(
            tenant_id=tenant_id,
            agent_id=agent_uuid,
            manifest_version=manifest.version,
        )
        if duplicate_version is not None:
            raise DuplicateAgentVersionError(
                f"Agent {agent_id} already has version {manifest.version}"
            )

        version = AgentVersion(
            agent_id=agent_uuid,
            manifest=manifest,
            status=LifecycleStatus.PUBLISHED,
            checksum=self._manifest_checksum(manifest),
        )
        saved_version = self.repository.save_version(version)

        if agent.status == LifecycleStatus.DRAFT:
            promoted_agent = agent.model_copy(update={"status": LifecycleStatus.PUBLISHED})
            self.repository.save_agent(promoted_agent)

        return saved_version

    def list_versions(self, tenant_id: str, agent_id: UUID | str) -> list[AgentVersion]:
        agent_uuid = self._parse_uuid(agent_id)
        if self.repository.get_agent(tenant_id, agent_uuid) is None:
            raise AgentNotFoundError(f"Agent not found: {agent_id}")
        return self.repository.list_versions(tenant_id, agent_uuid)

    def deprecate_agent(self, tenant_id: str, agent_id: UUID | str) -> AgentDefinition:
        agent = self.get_agent(tenant_id, agent_id)
        deprecated_agent = agent.model_copy(update={"status": LifecycleStatus.DEPRECATED})
        return self.repository.save_agent(deprecated_agent)

    @staticmethod
    def _manifest_checksum(manifest: AgentManifest) -> str:
        manifest_json = manifest.model_dump_json(exclude_none=True, by_alias=True)
        return sha256(manifest_json.encode("utf-8")).hexdigest()

    @staticmethod
    def _parse_uuid(value: UUID | str) -> UUID:
        if isinstance(value, UUID):
            return value
        return UUID(value)

