from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field


class ModelProfileRecord(BaseModel):
    profile_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelConfigService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save_profile(
        self,
        *,
        tenant_id: str,
        display_name: str,
        provider: str,
        model: str,
        api_key: str | None = None,
        profile_id: str | None = None,
    ) -> ModelProfileRecord:
        now = datetime.now(UTC)
        resolved_profile_id = profile_id or f"{provider}-{model}-{uuid4()}".lower().replace(" ", "-")
        existing = self.get_profile(tenant_id, resolved_profile_id)
        record = ModelProfileRecord(
            profile_id=resolved_profile_id,
            tenant_id=tenant_id,
            display_name=display_name,
            provider=provider,
            model=model,
            api_key=api_key,
            created_at=existing.created_at if existing else now,
            updated_at=now,
        )
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO model_profiles (
                    profile_id, tenant_id, display_name, provider, model, api_key, created_at, updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    display_name = excluded.display_name,
                    provider = excluded.provider,
                    model = excluded.model,
                    api_key = excluded.api_key,
                    updated_at = excluded.updated_at,
                    payload_json = excluded.payload_json
                """,
                (
                    record.profile_id,
                    record.tenant_id,
                    record.display_name,
                    record.provider,
                    record.model,
                    record.api_key,
                    record.created_at.isoformat(),
                    record.updated_at.isoformat(),
                    record.model_dump_json(),
                ),
            )
        return record

    def get_profile(self, tenant_id: str, profile_id: str) -> ModelProfileRecord | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload_json FROM model_profiles WHERE tenant_id = ? AND profile_id = ?",
                (tenant_id, profile_id),
            ).fetchone()
        return self._profile_from_row(row)

    def list_profiles(self, tenant_id: str) -> list[ModelProfileRecord]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                "SELECT payload_json FROM model_profiles WHERE tenant_id = ? ORDER BY created_at ASC",
                (tenant_id,),
            ).fetchall()
        return [ModelProfileRecord.model_validate_json(row["payload_json"]) for row in rows]

    def delete_profile(self, tenant_id: str, profile_id: str) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "DELETE FROM model_profiles WHERE tenant_id = ? AND profile_id = ?",
                (tenant_id, profile_id),
            )

    def _initialize_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS model_profiles (
                    profile_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    api_key TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_model_profiles_tenant_created
                    ON model_profiles (tenant_id, created_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _profile_from_row(row: sqlite3.Row | None) -> ModelProfileRecord | None:
        if row is None:
            return None
        return ModelProfileRecord.model_validate_json(row["payload_json"])
