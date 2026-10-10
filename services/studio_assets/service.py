from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from contextlib import closing
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RuleDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    HUMAN_REVIEW = "human_review"


class WorkflowNodeType(StrEnum):
    TRIGGER = "trigger"
    LLM = "llm"
    TOOL = "tool"
    RAG = "rag"
    RULE = "rule"
    HUMAN_APPROVAL = "human_approval"
    SUB_AGENT = "sub_agent"
    MCP = "mcp"
    API = "api"


class RuleDefinition(BaseModel):
    rule_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    condition: str = Field(min_length=1)
    decision: RuleDecision = RuleDecision.HUMAN_REVIEW
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkflowNode(BaseModel):
    node_id: UUID = Field(default_factory=uuid4)
    node_type: WorkflowNodeType
    name: str = Field(min_length=1)
    service_ref: str | None = None
    instruction: str | None = None
    position: int = 0


class WorkflowDefinition(BaseModel):
    workflow_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    nodes: list[WorkflowNode] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class StudioAssetRepository(ABC):
    @abstractmethod
    def save_rule(self, rule: RuleDefinition) -> RuleDefinition:
        raise NotImplementedError

    @abstractmethod
    def list_rules(self, tenant_id: str) -> list[RuleDefinition]:
        raise NotImplementedError

    @abstractmethod
    def save_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        raise NotImplementedError

    @abstractmethod
    def get_workflow(self, workflow_id: UUID) -> WorkflowDefinition | None:
        raise NotImplementedError

    @abstractmethod
    def list_workflows(self, tenant_id: str, agent_id: str | None = None) -> list[WorkflowDefinition]:
        raise NotImplementedError


class InMemoryStudioAssetRepository(StudioAssetRepository):
    def __init__(self) -> None:
        self._rules: dict[UUID, RuleDefinition] = {}
        self._workflows: dict[UUID, WorkflowDefinition] = {}

    def save_rule(self, rule: RuleDefinition) -> RuleDefinition:
        self._rules[rule.rule_id] = rule
        return rule

    def list_rules(self, tenant_id: str) -> list[RuleDefinition]:
        return sorted(
            [rule for rule in self._rules.values() if rule.tenant_id == tenant_id],
            key=lambda rule: rule.created_at,
        )

    def save_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        self._workflows[workflow.workflow_id] = workflow
        return workflow

    def get_workflow(self, workflow_id: UUID) -> WorkflowDefinition | None:
        return self._workflows.get(workflow_id)

    def list_workflows(self, tenant_id: str, agent_id: str | None = None) -> list[WorkflowDefinition]:
        return sorted(
            [
                workflow
                for workflow in self._workflows.values()
                if workflow.tenant_id == tenant_id and (agent_id is None or workflow.agent_id == agent_id)
            ],
            key=lambda workflow: workflow.updated_at,
        )


class SQLiteStudioAssetRepository(StudioAssetRepository):
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def save_rule(self, rule: RuleDefinition) -> RuleDefinition:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO studio_rules (
                    rule_id, tenant_id, name, decision, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(rule_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    name = excluded.name,
                    decision = excluded.decision,
                    payload_json = excluded.payload_json
                """,
                (
                    str(rule.rule_id),
                    rule.tenant_id,
                    rule.name,
                    rule.decision.value,
                    rule.created_at.isoformat(),
                    rule.model_dump_json(),
                ),
            )
        return rule

    def list_rules(self, tenant_id: str) -> list[RuleDefinition]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                "SELECT payload_json FROM studio_rules WHERE tenant_id = ? ORDER BY created_at ASC",
                (tenant_id,),
            ).fetchall()
        return [RuleDefinition.model_validate_json(row["payload_json"]) for row in rows]

    def save_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO studio_workflows (
                    workflow_id, tenant_id, agent_id, name, created_at, updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(workflow_id) DO UPDATE SET
                    tenant_id = excluded.tenant_id,
                    agent_id = excluded.agent_id,
                    name = excluded.name,
                    updated_at = excluded.updated_at,
                    payload_json = excluded.payload_json
                """,
                (
                    str(workflow.workflow_id),
                    workflow.tenant_id,
                    workflow.agent_id,
                    workflow.name,
                    workflow.created_at.isoformat(),
                    workflow.updated_at.isoformat(),
                    workflow.model_dump_json(),
                ),
            )
        return workflow

    def get_workflow(self, workflow_id: UUID) -> WorkflowDefinition | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT payload_json FROM studio_workflows WHERE workflow_id = ?",
                (str(workflow_id),),
            ).fetchone()
        if row is None:
            return None
        return WorkflowDefinition.model_validate_json(row["payload_json"])

    def list_workflows(self, tenant_id: str, agent_id: str | None = None) -> list[WorkflowDefinition]:
        query = "SELECT payload_json FROM studio_workflows WHERE tenant_id = ?"
        params = [tenant_id]
        if agent_id is not None:
            query += " AND agent_id = ?"
            params.append(agent_id)
        query += " ORDER BY updated_at ASC"
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(query, params).fetchall()
        return [WorkflowDefinition.model_validate_json(row["payload_json"]) for row in rows]

    def _initialize_schema(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS studio_rules (
                    rule_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_studio_rules_tenant_created
                    ON studio_rules (tenant_id, created_at);

                CREATE TABLE IF NOT EXISTS studio_workflows (
                    workflow_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_studio_workflows_agent_updated
                    ON studio_workflows (tenant_id, agent_id, updated_at);
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection


class StudioAssetService:
    def __init__(self, repository: StudioAssetRepository | None = None) -> None:
        self.repository = repository or InMemoryStudioAssetRepository()

    def create_rule(
        self,
        *,
        tenant_id: str,
        name: str,
        condition: str,
        decision: RuleDecision | str = RuleDecision.HUMAN_REVIEW,
    ) -> RuleDefinition:
        rule = RuleDefinition(
            tenant_id=tenant_id,
            name=name,
            condition=condition,
            decision=RuleDecision(decision),
        )
        return self.repository.save_rule(rule)

    def list_rules(self, tenant_id: str) -> list[RuleDefinition]:
        return self.repository.list_rules(tenant_id)

    def save_workflow(
        self,
        *,
        tenant_id: str,
        agent_id: str,
        name: str,
        nodes: list[WorkflowNode | dict],
        workflow_id: UUID | str | None = None,
    ) -> WorkflowDefinition:
        parsed_nodes = [node if isinstance(node, WorkflowNode) else WorkflowNode(**node) for node in nodes]
        workflow_uuid = self._parse_uuid(workflow_id) if workflow_id else uuid4()
        existing_workflow = self.repository.get_workflow(workflow_uuid)
        created_at = existing_workflow.created_at if existing_workflow else datetime.now(UTC)
        workflow = WorkflowDefinition(
            workflow_id=workflow_uuid,
            tenant_id=tenant_id,
            agent_id=agent_id,
            name=name,
            nodes=parsed_nodes,
            created_at=created_at,
            updated_at=datetime.now(UTC),
        )
        return self.repository.save_workflow(workflow)

    def list_workflows(self, tenant_id: str, agent_id: str | None = None) -> list[WorkflowDefinition]:
        return self.repository.list_workflows(tenant_id, agent_id)

    @staticmethod
    def _parse_uuid(value: UUID | str) -> UUID:
        if isinstance(value, UUID):
            return value
        return UUID(value)
