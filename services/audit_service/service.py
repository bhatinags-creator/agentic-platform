from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from platform_common.events.envelope import EventEnvelope


class AuditRepository:
    def save_event(self, event: EventEnvelope) -> EventEnvelope:
        raise NotImplementedError

    def list_events(
        self, tenant_id: str | None = None, trace_id: str | None = None
    ) -> list[EventEnvelope]:
        raise NotImplementedError


class InMemoryAuditRepository(AuditRepository):
    def __init__(self) -> None:
        self.records: list[EventEnvelope] = []

    def save_event(self, event: EventEnvelope) -> EventEnvelope:
        self.records.append(event)
        return event

    def list_events(
        self, tenant_id: str | None = None, trace_id: str | None = None
    ) -> list[EventEnvelope]:
        return [
            event
            for event in self.records
            if (tenant_id is None or event.tenant_id == tenant_id)
            and (trace_id is None or event.trace_id == trace_id)
        ]


class SQLiteAuditRepository(AuditRepository):
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save_event(self, event: EventEnvelope) -> EventEnvelope:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO audit_events (
                    event_id, tenant_id, trace_id, correlation_id, event_type,
                    occurred_at, idempotency_key, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(event.event_id),
                    event.tenant_id,
                    event.trace_id,
                    event.correlation_id,
                    event.event_type,
                    event.occurred_at.isoformat(),
                    event.idempotency_key,
                    event.model_dump_json(),
                ),
            )
        return event

    def list_events(
        self, tenant_id: str | None = None, trace_id: str | None = None
    ) -> list[EventEnvelope]:
        query = "SELECT payload_json FROM audit_events WHERE 1 = 1"
        params: list[str] = []
        if tenant_id is not None:
            query += " AND tenant_id = ?"
            params.append(tenant_id)
        if trace_id is not None:
            query += " AND trace_id = ?"
            params.append(trace_id)
        query += " ORDER BY occurred_at ASC"
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(query, params).fetchall()
        return [EventEnvelope.model_validate_json(row["payload_json"]) for row in rows]

    def _initialize_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    event_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    correlation_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    idempotency_key TEXT,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_audit_events_tenant_trace
                    ON audit_events (tenant_id, trace_id, occurred_at);

                CREATE INDEX IF NOT EXISTS idx_audit_events_type
                    ON audit_events (event_type);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection


class AuditService:
    def __init__(self, repository: AuditRepository | None = None) -> None:
        self.repository = repository or InMemoryAuditRepository()

    @property
    def records(self) -> list[EventEnvelope]:
        return self.repository.list_events()

    def write(self, event: EventEnvelope) -> EventEnvelope:
        return self.repository.save_event(event)

    def list_events(self, tenant_id: str, trace_id: str | None = None) -> list[EventEnvelope]:
        return self.repository.list_events(tenant_id=tenant_id, trace_id=trace_id)

