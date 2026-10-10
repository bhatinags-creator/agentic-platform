from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import UUID

from services.agent_studio.service import (
    AgentDraft,
    AgentDraftRepository,
    AgentInteractionRepository,
    AgentInteractionResult,
)


class SQLiteAgentDraftRepository(AgentDraftRepository):
    """SQLite-backed Agent Studio draft repository for local durable deployments."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save_draft(self, draft: AgentDraft) -> AgentDraft:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO agent_studio_drafts (
                    draft_id,
                    tenant_id,
                    name,
                    owner,
                    risk_class,
                    status,
                    agent_id,
                    published_version_id,
                    created_at,
                    updated_at,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(draft_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    name = excluded.name,
                    owner = excluded.owner,
                    risk_class = excluded.risk_class,
                    status = excluded.status,
                    agent_id = excluded.agent_id,
                    published_version_id = excluded.published_version_id,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at,
                    payload_json = excluded.payload_json
                """,
                (
                    str(draft.draft_id),
                    draft.tenant_id,
                    draft.name,
                    draft.owner,
                    draft.risk_class.value,
                    draft.status.value,
                    str(draft.agent_id) if draft.agent_id else None,
                    str(draft.published_version_id) if draft.published_version_id else None,
                    draft.created_at.isoformat(),
                    draft.updated_at.isoformat(),
                    draft.model_dump_json(),
                ),
            )
        return draft

    def get_draft(self, tenant_id: str, draft_id: UUID) -> AgentDraft | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM agent_studio_drafts
                WHERE tenant_id = ? AND draft_id = ?
                """,
                (tenant_id, str(draft_id)),
            ).fetchone()
        return self._draft_from_row(row)

    def list_drafts(self, tenant_id: str) -> list[AgentDraft]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM agent_studio_drafts
                WHERE tenant_id = ?
                ORDER BY created_at ASC
                """,
                (tenant_id,),
            ).fetchall()
        return [AgentDraft.model_validate_json(row["payload_json"]) for row in rows]

    def _initialize_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_studio_drafts (
                    draft_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    risk_class TEXT NOT NULL,
                    status TEXT NOT NULL,
                    agent_id TEXT,
                    published_version_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_agent_studio_drafts_tenant_created
                    ON agent_studio_drafts (tenant_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_agent_studio_drafts_tenant_name_updated
                    ON agent_studio_drafts (tenant_id, name, updated_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _draft_from_row(row: sqlite3.Row | None) -> AgentDraft | None:
        if row is None:
            return None
        return AgentDraft.model_validate_json(row["payload_json"])


class SQLiteAgentInteractionRepository(AgentInteractionRepository):
    """SQLite-backed Testing Studio interaction repository."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save_interaction(self, interaction: AgentInteractionResult, tenant_id: str) -> AgentInteractionResult:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO agent_studio_interactions (
                    interaction_id, tenant_id, draft_id, agent_name, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(interaction_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    draft_id = excluded.draft_id,
                    agent_name = excluded.agent_name,
                    payload_json = excluded.payload_json
                """,
                (
                    str(interaction.interaction_id),
                    tenant_id,
                    str(interaction.draft_id),
                    interaction.agent_name,
                    interaction.created_at.isoformat(),
                    interaction.model_dump_json(),
                ),
            )
        return interaction

    def list_interactions(self, tenant_id: str, draft_id: UUID | None = None) -> list[AgentInteractionResult]:
        query = "SELECT payload_json FROM agent_studio_interactions WHERE tenant_id = ?"
        params = [tenant_id]
        if draft_id is not None:
            query += " AND draft_id = ?"
            params.append(str(draft_id))
        query += " ORDER BY created_at ASC"
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(query, params).fetchall()
        return [AgentInteractionResult.model_validate_json(row["payload_json"]) for row in rows]

    def _initialize_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_studio_interactions (
                    interaction_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    draft_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_agent_studio_interactions_draft_created
                    ON agent_studio_interactions (tenant_id, draft_id, created_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection
