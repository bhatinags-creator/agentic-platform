import pytest

from services.human_task_service.service import (
    HumanTaskAlreadyDecidedError,
    HumanTaskService,
    HumanTaskStatus,
)


def test_human_task_service_creates_and_approves_task() -> None:
    service = HumanTaskService()
    task = service.create_approval_task(
        tenant_id="tenant-a",
        run_id="run-1",
        prompt="Approve this run",
        assigned_to="manager-1",
    )

    approved = service.decide_task(
        tenant_id="tenant-a",
        task_id=task.human_task_id,
        approved=True,
        decided_by="manager-1",
        comment="looks good",
    )

    assert approved.status == HumanTaskStatus.APPROVED
    assert approved.decided_by == "manager-1"
    assert service.list_tasks("tenant-a", status="approved") == [approved]


def test_human_task_cannot_be_decided_twice() -> None:
    service = HumanTaskService()
    task = service.create_approval_task(tenant_id="tenant-a", run_id="run-1", prompt="Approve")
    service.decide_task(
        tenant_id="tenant-a",
        task_id=task.human_task_id,
        approved=False,
        decided_by="manager-1",
    )

    with pytest.raises(HumanTaskAlreadyDecidedError):
        service.decide_task(
            tenant_id="tenant-a",
            task_id=task.human_task_id,
            approved=True,
            decided_by="manager-2",
        )
