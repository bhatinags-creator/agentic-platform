from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import UUID

from platform_common.domain.models import AgentDefinition, AgentVersion
from services.agent_registry.service import AgentRegistryRepository


class SQLiteAgentRegistryRepository(AgentRegistryRepository):
    """SQLite-backed Agent Registry repository for local durable deployments."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save_agent(self, agent: AgentDefinition) -> AgentDefinition:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO agents (
                    agent_id, tenant_id, name, owner, risk_class, status, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    name = excluded.name,
                    owner = excluded.owner,
                    risk_class = excluded.risk_class,
                    status = excluded.status,
                    created_at = excluded.created_at,
                    payload_json = excluded.payload_json
                """,
                (
                    str(agent.agent_id),
                    agent.tenant_id,
                    agent.name,
                    agent.owner,
                    agent.risk_class.value,
                    agent.status.value,
                    agent.created_at.isoformat(),
                    agent.model_dump_json(),
                ),
            )
        return agent

    def get_agent(self, tenant_id: str, agent_id: UUID) -> AgentDefinition | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM agents
                WHERE tenant_id = ? AND agent_id = ?
                """,
                (tenant_id, str(agent_id)),
            ).fetchone()
        return self._agent_from_row(row)

    def find_agent_by_name(self, tenant_id: str, name: str) -> AgentDefinition | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM agents
                WHERE tenant_id = ? AND normalized_name = ?
                """,
                (tenant_id, name.casefold()),
            ).fetchone()
        return self._agent_from_row(row)

    def list_agents(self, tenant_id: str) -> list[AgentDefinition]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM agents
                WHERE tenant_id = ?
                ORDER BY created_at ASC
                """,
                (tenant_id,),
            ).fetchall()
        return [AgentDefinition.model_validate_json(row["payload_json"]) for row in rows]

    def save_version(self, version: AgentVersion) -> AgentVersion:
        with closing(self._connect()) as connection, connection:
            agent = connection.execute(
                """
                SELECT tenant_id
                FROM agents
                WHERE agent_id = ?
                """,
                (str(version.agent_id),),
            ).fetchone()
            if agent is None:
                raise ValueError(f"Cannot save version for unknown agent: {version.agent_id}")

            connection.execute(
                """
                INSERT INTO agent_versions (
                    version_id,
                    tenant_id,
                    agent_id,
                    manifest_id,
                    manifest_version,
                    status,
                    checksum,
                    created_at,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(version_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    agent_id = excluded.agent_id,
                    manifest_id = excluded.manifest_id,
                    manifest_version = excluded.manifest_version,
                    status = excluded.status,
                    checksum = excluded.checksum,
                    created_at = excluded.created_at,
                    payload_json = excluded.payload_json
                """,
                (
                    str(version.version_id),
                    agent["tenant_id"],
                    str(version.agent_id),
                    version.manifest.id,
                    version.manifest.version,
                    version.status.value,
                    version.checksum,
                    version.created_at.isoformat(),
                    version.model_dump_json(),
                ),
            )
        return version

    def get_version(self, tenant_id: str, version_id: UUID) -> AgentVersion | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM agent_versions
                WHERE tenant_id = ? AND version_id = ?
                """,
                (tenant_id, str(version_id)),
            ).fetchone()
        return self._version_from_row(row)

    def find_version_by_manifest_version(
        self, tenant_id: str, agent_id: UUID, manifest_version: str
    ) -> AgentVersion | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM agent_versions
                WHERE tenant_id = ? AND agent_id = ? AND manifest_version = ?
                """,
                (tenant_id, str(agent_id), manifest_version),
            ).fetchone()
        return self._version_from_row(row)

    def list_versions(self, tenant_id: str, agent_id: UUID) -> list[AgentVersion]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM agent_versions
                WHERE tenant_id = ? AND agent_id = ?
                ORDER BY created_at ASC
                """,
                (tenant_id, str(agent_id)),
            ).fetchall()
        return [AgentVersion.model_validate_json(row["payload_json"]) for row in rows]

    def _initialize_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    normalized_name TEXT GENERATED ALWAYS AS (lower(name)) STORED,
                    owner TEXT NOT NULL,
                    risk_class TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE (tenant_id, normalized_name)
                );

                CREATE INDEX IF NOT EXISTS idx_agents_tenant_created
                    ON agents (tenant_id, created_at);

                CREATE TABLE IF NOT EXISTS agent_versions (
                    version_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    manifest_id TEXT NOT NULL,
                    manifest_version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    checksum TEXT,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    UNIQUE (tenant_id, agent_id, manifest_version),
                    FOREIGN KEY(agent_id) REFERENCES agents(agent_id)
                );

                CREATE INDEX IF NOT EXISTS idx_agent_versions_agent_created
                    ON agent_versions (tenant_id, agent_id, created_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _agent_from_row(row: sqlite3.Row | None) -> AgentDefinition | None:
        if row is None:
            return None
        return AgentDefinition.model_validate_json(row["payload_json"])

    @staticmethod
    def _version_from_row(row: sqlite3.Row | None) -> AgentVersion | None:
        if row is None:
            return None
        return AgentVersion.model_validate_json(row["payload_json"])

