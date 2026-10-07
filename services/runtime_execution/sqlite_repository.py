from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import UUID

from platform_common.domain.models import AgentRun
from services.runtime_execution.service import AgentRunRepository


class SQLiteAgentRunRepository(AgentRunRepository):
    """SQLite-backed runtime run repository for local durable run history."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save_run(self, run: AgentRun) -> AgentRun:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO agent_runs (
                    run_id, tenant_id, agent_id, agent_version, user_id,
                    trace_id, status, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    agent_id = excluded.agent_id,
                    agent_version = excluded.agent_version,
                    user_id = excluded.user_id,
                    trace_id = excluded.trace_id,
                    status = excluded.status,
                    created_at = excluded.created_at,
                    payload_json = excluded.payload_json
                """,
                (
                    str(run.run_id),
                    run.tenant_id,
                    run.agent_id,
                    run.agent_version,
                    run.user_id,
                    run.trace_id,
                    run.status.value,
                    run.created_at.isoformat(),
                    run.model_dump_json(),
                ),
            )
        return run

    def get_run(self, tenant_id: str, run_id: UUID) -> AgentRun | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM agent_runs
                WHERE tenant_id = ? AND run_id = ?
                """,
                (tenant_id, str(run_id)),
            ).fetchone()
        if row is None:
            return None
        return AgentRun.model_validate_json(row["payload_json"])

    def list_runs(self, tenant_id: str) -> list[AgentRun]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM agent_runs
                WHERE tenant_id = ?
                ORDER BY created_at ASC
                """,
                (tenant_id,),
            ).fetchall()
        return [AgentRun.model_validate_json(row["payload_json"]) for row in rows]

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_runs (
                    run_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    agent_version TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_agent_runs_tenant_created
                    ON agent_runs (tenant_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_agent_runs_tenant_agent
                    ON agent_runs (tenant_id, agent_id);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection
