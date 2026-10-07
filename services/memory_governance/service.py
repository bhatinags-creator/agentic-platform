from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

from platform_common.domain.models import RetentionPolicy


class MemoryType(StrEnum):
    SESSION = "session"
    CONVERSATION = "conversation"
    AGENT_WORKING_MEMORY = "agent_working_memory"
    SEMANTIC_MEMORY = "semantic_memory"
    HUMAN_DECISIONS = "human_decisions"


MEMORY_RETENTION_DEFAULTS: dict[MemoryType, RetentionPolicy] = {
    MemoryType.SESSION: RetentionPolicy.HOURS_24,
    MemoryType.CONVERSATION: RetentionPolicy.DAYS_90,
    MemoryType.AGENT_WORKING_MEMORY: RetentionPolicy.RUNTIME_ONLY,
    MemoryType.SEMANTIC_MEMORY: RetentionPolicy.POLICY_CONTROLLED,
    MemoryType.HUMAN_DECISIONS: RetentionPolicy.YEARS_7,
}


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: UUID
    tenant_id: str
    agent_id: str
    run_id: str
    trace_id: str
    memory_type: MemoryType
    retention: RetentionPolicy
    content: dict
    created_at: datetime
    expires_at: datetime | None
    policy_ref: str | None = None


class MemoryRepository:
    def save_record(self, record: MemoryRecord) -> MemoryRecord:
        raise NotImplementedError

    def list_records(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        memory_type: MemoryType | None = None,
    ) -> list[MemoryRecord]:
        raise NotImplementedError

    def delete_records(self, memory_ids: list[UUID]) -> None:
        raise NotImplementedError


class InMemoryMemoryRepository(MemoryRepository):
    def __init__(self) -> None:
        self.records: list[MemoryRecord] = []

    def save_record(self, record: MemoryRecord) -> MemoryRecord:
        self.records.append(record)
        return record

    def list_records(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        memory_type: MemoryType | None = None,
    ) -> list[MemoryRecord]:
        return [
            record
            for record in self.records
            if (tenant_id is None or record.tenant_id == tenant_id)
            and (agent_id is None or record.agent_id == agent_id)
            and (run_id is None or record.run_id == run_id)
            and (memory_type is None or record.memory_type == memory_type)
        ]

    def delete_records(self, memory_ids: list[UUID]) -> None:
        self.records = [record for record in self.records if record.memory_id not in memory_ids]


class SQLiteMemoryRepository(MemoryRepository):
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save_record(self, record: MemoryRecord) -> MemoryRecord:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO memory_records (
                    memory_id, tenant_id, agent_id, run_id, trace_id, memory_type,
                    retention, content_json, created_at, expires_at, policy_ref
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(memory_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    agent_id = excluded.agent_id,
                    run_id = excluded.run_id,
                    trace_id = excluded.trace_id,
                    memory_type = excluded.memory_type,
                    retention = excluded.retention,
                    content_json = excluded.content_json,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at,
                    policy_ref = excluded.policy_ref
                """,
                self._record_to_row(record),
            )
        return record

    def list_records(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        memory_type: MemoryType | None = None,
    ) -> list[MemoryRecord]:
        query = "SELECT * FROM memory_records WHERE 1 = 1"
        params: list[str] = []
        if tenant_id is not None:
            query += " AND tenant_id = ?"
            params.append(tenant_id)
        if agent_id is not None:
            query += " AND agent_id = ?"
            params.append(agent_id)
        if run_id is not None:
            query += " AND run_id = ?"
            params.append(run_id)
        if memory_type is not None:
            query += " AND memory_type = ?"
            params.append(memory_type.value)
        query += " ORDER BY created_at ASC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._record_from_row(row) for row in rows]

    def delete_records(self, memory_ids: list[UUID]) -> None:
        if not memory_ids:
            return
        placeholders = ", ".join("?" for _ in memory_ids)
        with self._connect() as connection:
            connection.execute(
                f"DELETE FROM memory_records WHERE memory_id IN ({placeholders})",
                [str(memory_id) for memory_id in memory_ids],
            )

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS memory_records (
                    memory_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    retention TEXT NOT NULL,
                    content_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    policy_ref TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_memory_records_tenant_agent
                    ON memory_records (tenant_id, agent_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_memory_records_expiry
                    ON memory_records (expires_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _record_to_row(record: MemoryRecord) -> tuple:
        return (
            str(record.memory_id),
            record.tenant_id,
            record.agent_id,
            record.run_id,
            record.trace_id,
            record.memory_type.value,
            record.retention.value,
            json.dumps(record.content),
            record.created_at.isoformat(),
            record.expires_at.isoformat() if record.expires_at else None,
            record.policy_ref,
        )

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            memory_id=UUID(row["memory_id"]),
            tenant_id=row["tenant_id"],
            agent_id=row["agent_id"],
            run_id=row["run_id"],
            trace_id=row["trace_id"],
            memory_type=MemoryType(row["memory_type"]),
            retention=RetentionPolicy(row["retention"]),
            content=json.loads(row["content_json"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            policy_ref=row["policy_ref"],
        )


class MemoryGovernanceService:
    def __init__(self, repository: MemoryRepository | None = None) -> None:
        self.repository = repository or InMemoryMemoryRepository()

    @property
    def records(self) -> list[MemoryRecord]:
        return self.list_records()

    def retention_for(self, memory_type: str | MemoryType) -> str:
        resolved_memory_type = self._parse_memory_type(memory_type)
        return MEMORY_RETENTION_DEFAULTS.get(
            resolved_memory_type,
            RetentionPolicy.POLICY_CONTROLLED,
        ).value

    def create_record(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        run_id: str,
        trace_id: str,
        memory_type: str | MemoryType,
        content: dict,
        policy_ref: str | None = None,
    ) -> MemoryRecord:
        resolved_memory_type = self._parse_memory_type(memory_type)
        retention = MEMORY_RETENTION_DEFAULTS.get(
            resolved_memory_type,
            RetentionPolicy.POLICY_CONTROLLED,
        )
        created_at = datetime.now(UTC)
        record = MemoryRecord(
            memory_id=uuid4(),
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            trace_id=trace_id,
            memory_type=resolved_memory_type,
            retention=retention,
            content=content,
            created_at=created_at,
            expires_at=self._expires_at(created_at, retention),
            policy_ref=policy_ref,
        )
        return self.repository.save_record(record)

    def list_records(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        memory_type: str | MemoryType | None = None,
    ) -> list[MemoryRecord]:
        resolved_memory_type = self._parse_memory_type(memory_type) if memory_type else None
        return self.repository.list_records(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            memory_type=resolved_memory_type,
        )

    def purge_expired(self, now: datetime | None = None) -> list[MemoryRecord]:
        current_time = now or datetime.now(UTC)
        expired_records = [
            record
            for record in self.list_records()
            if record.expires_at is not None and record.expires_at <= current_time
        ]
        self.repository.delete_records([record.memory_id for record in expired_records])
        return expired_records

    @staticmethod
    def _parse_memory_type(memory_type: str | MemoryType) -> MemoryType:
        if isinstance(memory_type, MemoryType):
            return memory_type
        return MemoryType(memory_type)

    @staticmethod
    def _expires_at(created_at: datetime, retention: RetentionPolicy) -> datetime | None:
        match retention:
            case RetentionPolicy.RUNTIME_ONLY:
                return created_at
            case RetentionPolicy.HOURS_24:
                return created_at + timedelta(hours=24)
            case RetentionPolicy.DAYS_90:
                return created_at + timedelta(days=90)
            case RetentionPolicy.YEARS_7:
                return created_at + timedelta(days=365 * 7)
            case RetentionPolicy.POLICY_CONTROLLED:
                return None
