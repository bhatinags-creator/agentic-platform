from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class HumanTaskStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class HumanTask(BaseModel):
    human_task_id: UUID = Field(default_factory=uuid4)
    tenant_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    status: HumanTaskStatus = HumanTaskStatus.PENDING
    prompt: str = Field(min_length=1)
    assigned_to: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_at: datetime | None = None
    decided_by: str | None = None
    decision_comment: str | None = None


class HumanApprovalDecision(BaseModel):
    task_id: UUID
    approved: bool
    decided_by: str
    comment: str | None = None
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HumanTaskNotFoundError(Exception):
    """Raised when a human task is not visible to the requested tenant."""


class HumanTaskAlreadyDecidedError(Exception):
    """Raised when a caller tries to decide an already completed task."""


class HumanTaskService:
    def __init__(self) -> None:
        self._tasks: dict[UUID, HumanTask] = {}

    def create_approval_task(
        self,
        run_id: str,
        prompt: str,
        *,
        tenant_id: str = "default",
        assigned_to: str | None = None,
    ) -> HumanTask:
        task = HumanTask(
            tenant_id=tenant_id,
            run_id=run_id,
            prompt=prompt,
            assigned_to=assigned_to,
        )
        self._tasks[task.human_task_id] = task
        return task

    def decide_task(
        self,
        *,
        tenant_id: str,
        task_id: UUID | str,
        approved: bool,
        decided_by: str,
        comment: str | None = None,
    ) -> HumanTask:
        task = self.get_task(tenant_id, task_id)
        if task.status != HumanTaskStatus.PENDING:
            raise HumanTaskAlreadyDecidedError(f"Human task already decided: {task_id}")
        updated = task.model_copy(
            update={
                "status": HumanTaskStatus.APPROVED if approved else HumanTaskStatus.REJECTED,
                "decided_at": datetime.now(UTC),
                "decided_by": decided_by,
                "decision_comment": comment,
            }
        )
        self._tasks[updated.human_task_id] = updated
        return updated

    def get_task(self, tenant_id: str, task_id: UUID | str) -> HumanTask:
        task_uuid = self._parse_uuid(task_id)
        task = self._tasks.get(task_uuid)
        if task is None or task.tenant_id != tenant_id:
            raise HumanTaskNotFoundError(f"Human task not found: {task_id}")
        return task

    def list_tasks(
        self,
        tenant_id: str,
        status: HumanTaskStatus | str | None = None,
    ) -> list[HumanTask]:
        resolved_status = HumanTaskStatus(status) if status else None
        return sorted(
            [
                task
                for task in self._tasks.values()
                if task.tenant_id == tenant_id
                and (resolved_status is None or task.status == resolved_status)
            ],
            key=lambda task: task.created_at,
        )

    @staticmethod
    def _parse_uuid(value: UUID | str) -> UUID:
        if isinstance(value, UUID):
            return value
        return UUID(value)
