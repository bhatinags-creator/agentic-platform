from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4


@dataclass(frozen=True)
class CostEvent:
    event_id: UUID
    tenant_id: str
    agent_id: str
    run_id: str
    trace_id: str
    workflow_id: str | None
    department: str | None
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    occurred_at: datetime


@dataclass(frozen=True)
class CostSummary:
    tenant_id: str
    total_runs: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_tokens: int
    total_cost: float


class BudgetExceededError(Exception):
    """Raised when a cost event would exceed a tenant budget."""


class FinOpsRepository:
    def save_event(self, event: CostEvent) -> CostEvent:
        raise NotImplementedError

    def list_events(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        department: str | None = None,
    ) -> list[CostEvent]:
        raise NotImplementedError


class InMemoryFinOpsRepository(FinOpsRepository):
    def __init__(self) -> None:
        self.events: list[CostEvent] = []

    def save_event(self, event: CostEvent) -> CostEvent:
        self.events.append(event)
        return event

    def list_events(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        department: str | None = None,
    ) -> list[CostEvent]:
        return [
            event
            for event in self.events
            if (tenant_id is None or event.tenant_id == tenant_id)
            and (agent_id is None or event.agent_id == agent_id)
            and (run_id is None or event.run_id == run_id)
            and (department is None or event.department == department)
        ]


class SQLiteFinOpsRepository(FinOpsRepository):
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save_event(self, event: CostEvent) -> CostEvent:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO cost_events (
                    event_id, tenant_id, agent_id, run_id, trace_id, workflow_id,
                    department, provider, model, prompt_tokens, completion_tokens,
                    total_tokens, estimated_cost, occurred_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    agent_id = excluded.agent_id,
                    run_id = excluded.run_id,
                    trace_id = excluded.trace_id,
                    workflow_id = excluded.workflow_id,
                    department = excluded.department,
                    provider = excluded.provider,
                    model = excluded.model,
                    prompt_tokens = excluded.prompt_tokens,
                    completion_tokens = excluded.completion_tokens,
                    total_tokens = excluded.total_tokens,
                    estimated_cost = excluded.estimated_cost,
                    occurred_at = excluded.occurred_at
                """,
                self._event_to_row(event),
            )
        return event

    def list_events(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        department: str | None = None,
    ) -> list[CostEvent]:
        query = "SELECT * FROM cost_events WHERE 1 = 1"
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
        if department is not None:
            query += " AND department = ?"
            params.append(department)
        query += " ORDER BY occurred_at ASC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._event_from_row(row) for row in rows]

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS cost_events (
                    event_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    trace_id TEXT NOT NULL,
                    workflow_id TEXT,
                    department TEXT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    total_tokens INTEGER NOT NULL,
                    estimated_cost REAL NOT NULL,
                    occurred_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_cost_events_tenant_agent
                    ON cost_events (tenant_id, agent_id, occurred_at);

                CREATE INDEX IF NOT EXISTS idx_cost_events_tenant_department
                    ON cost_events (tenant_id, department, occurred_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _event_to_row(event: CostEvent) -> tuple:
        return (
            str(event.event_id),
            event.tenant_id,
            event.agent_id,
            event.run_id,
            event.trace_id,
            event.workflow_id,
            event.department,
            event.provider,
            event.model,
            event.prompt_tokens,
            event.completion_tokens,
            event.total_tokens,
            event.estimated_cost,
            event.occurred_at.isoformat(),
        )

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> CostEvent:
        return CostEvent(
            event_id=UUID(row["event_id"]),
            tenant_id=row["tenant_id"],
            agent_id=row["agent_id"],
            run_id=row["run_id"],
            trace_id=row["trace_id"],
            workflow_id=row["workflow_id"],
            department=row["department"],
            provider=row["provider"],
            model=row["model"],
            prompt_tokens=row["prompt_tokens"],
            completion_tokens=row["completion_tokens"],
            total_tokens=row["total_tokens"],
            estimated_cost=row["estimated_cost"],
            occurred_at=datetime.fromisoformat(row["occurred_at"]),
        )


class AIFinOpsService:
    def __init__(self, repository: FinOpsRepository | None = None) -> None:
        self.repository = repository or InMemoryFinOpsRepository()
        self.tenant_budgets: dict[str, float] = {}

    @property
    def events(self) -> list[CostEvent]:
        return self.list_events()

    def set_tenant_budget(self, tenant_id: str, budget: float) -> None:
        if budget < 0:
            raise ValueError("budget must be greater than or equal to zero")
        self.tenant_budgets[tenant_id] = budget

    def record_model_usage(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        run_id: str,
        trace_id: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost: float,
        workflow_id: str | None = None,
        department: str | None = None,
    ) -> CostEvent:
        projected_cost = self.total_cost_by_tenant(tenant_id) + estimated_cost
        budget = self.tenant_budgets.get(tenant_id)
        if budget is not None and projected_cost > budget:
            raise BudgetExceededError(
                f"Tenant {tenant_id} budget exceeded: projected={projected_cost}, budget={budget}"
            )

        event = CostEvent(
            event_id=uuid4(),
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
            department=department,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost=estimated_cost,
            occurred_at=datetime.now(UTC),
        )
        return self.repository.save_event(event)

    def list_events(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        run_id: str | None = None,
        department: str | None = None,
    ) -> list[CostEvent]:
        return self.repository.list_events(
            tenant_id=tenant_id,
            agent_id=agent_id,
            run_id=run_id,
            department=department,
        )

    def summarize_tenant(self, tenant_id: str) -> CostSummary:
        events = self.list_events(tenant_id=tenant_id)
        return CostSummary(
            tenant_id=tenant_id,
            total_runs=len({event.run_id for event in events}),
            total_prompt_tokens=sum(event.prompt_tokens for event in events),
            total_completion_tokens=sum(event.completion_tokens for event in events),
            total_tokens=sum(event.total_tokens for event in events),
            total_cost=sum(event.estimated_cost for event in events),
        )

    def total_cost_by_tenant(self, tenant_id: str) -> float:
        return self.summarize_tenant(tenant_id).total_cost

    def total_cost_by_agent(self, tenant_id: str, agent_id: str) -> float:
        return sum(
            event.estimated_cost
            for event in self.list_events(tenant_id=tenant_id, agent_id=agent_id)
        )

    def total_cost_by_department(self, tenant_id: str, department: str) -> float:
        return sum(
            event.estimated_cost
            for event in self.list_events(tenant_id=tenant_id, department=department)
        )
