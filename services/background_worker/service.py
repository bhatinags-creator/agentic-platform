from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class WorkerJobStatus(StrEnum):
    QUEUED = "queued"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkerJob:
    job_id: UUID = field(default_factory=uuid4)
    job_type: str = "generic"
    payload: dict = field(default_factory=dict)
    status: WorkerJobStatus = WorkerJobStatus.QUEUED
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None


class BackgroundWorkerService:
    def __init__(self) -> None:
        self.jobs: dict[UUID, WorkerJob] = {}

    def enqueue(self, job_type: str, payload: dict) -> WorkerJob:
        job = WorkerJob(job_type=job_type, payload=payload)
        self.jobs[job.job_id] = job
        return job

    def run_next(self) -> WorkerJob | None:
        queued = [job for job in self.jobs.values() if job.status == WorkerJobStatus.QUEUED]
        if not queued:
            return None
        job = min(queued, key=lambda item: item.created_at)
        job.status = WorkerJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        self.jobs[job.job_id] = job
        return job

    def list_jobs(self, status: WorkerJobStatus | str | None = None) -> list[WorkerJob]:
        resolved = WorkerJobStatus(status) if status else None
        return sorted(
            [job for job in self.jobs.values() if resolved is None or job.status == resolved],
            key=lambda job: job.created_at,
        )
