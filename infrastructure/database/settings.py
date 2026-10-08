from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar


class DatabaseEngine(StrEnum):
    SQLITE = "sqlite"
    POSTGRES = "postgres"


@dataclass(frozen=True)
class DatabaseSettings:
    engine: DatabaseEngine
    url: str
    pool_size: int = 5

    @classmethod
    def from_url(cls, url: str) -> DatabaseSettings:
        if url.startswith("postgresql"):
            return cls(engine=DatabaseEngine.POSTGRES, url=url)
        return cls(engine=DatabaseEngine.SQLITE, url=url, pool_size=1)


class PostgresMigrationPlan:
    steps: ClassVar[list[str]] = [
        "replace SQLite repositories with Postgres repository implementations",
        "introduce migration tooling before schema changes",
        "move runtime/audit/finops/memory tables to Postgres",
        "run dual-write or export/import migration for local data",
        "promote DATABASE_URL as the production database configuration",
    ]

    def describe(self) -> list[str]:
        return list(self.steps)
