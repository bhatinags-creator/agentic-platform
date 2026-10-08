from services.background_worker.service import BackgroundWorkerService, WorkerJobStatus


def test_background_worker_runs_queued_jobs_in_creation_order() -> None:
    service = BackgroundWorkerService()
    first = service.enqueue("evaluation.run", {"suite": "smoke"})
    second = service.enqueue("deployment.promote", {"deployment": "dev"})

    completed = service.run_next()

    assert completed == first
    assert completed.status == WorkerJobStatus.COMPLETED
    assert completed.completed_at is not None
    assert service.list_jobs(WorkerJobStatus.QUEUED) == [second]


def test_background_worker_returns_none_when_queue_is_empty() -> None:
    service = BackgroundWorkerService()

    assert service.run_next() is None
