from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TraceStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING = "waiting"


class SpanStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TraceRecord(BaseModel):
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(min_length=1)
    run_id: str | None = None
    agent_id: str | None = None
    status: TraceStatus = TraceStatus.RUNNING
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class SpanRecord(BaseModel):
    span_id: UUID = Field(default_factory=uuid4)
    trace_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: SpanStatus = SpanStatus.RUNNING
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ended_at: datetime | None = None
    attributes: dict = Field(default_factory=dict)
    error: str | None = None


class MetricsSnapshot(BaseModel):
    tenant_id: str
    total_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    waiting_runs: int = 0
    policy_denials: int = 0
    total_cost: float = 0.0
    total_tokens: int = 0
    memory_records: int = 0
    open_traces: int = 0
    completed_traces: int = 0


class TraceNotFoundError(Exception):
    """Raised when a trace is not visible to the requested tenant."""


class SpanNotFoundError(Exception):
    """Raised when a span cannot be found."""


class ObservabilityService:
    def __init__(self) -> None:
        self._traces: dict[str, TraceRecord] = {}
        self._spans: dict[UUID, SpanRecord] = {}

    def start_trace(
        self,
        *,
        tenant_id: str,
        trace_id: str | None = None,
        run_id: str | None = None,
        agent_id: str | None = None,
        metadata: dict | None = None,
    ) -> TraceRecord:
        trace = TraceRecord(
            trace_id=trace_id or str(uuid4()),
            tenant_id=tenant_id,
            run_id=run_id,
            agent_id=agent_id,
            metadata=metadata or {},
        )
        self._traces[trace.trace_id] = trace
        return trace

    def finish_trace(
        self,
        tenant_id: str,
        trace_id: str,
        status: TraceStatus | str = TraceStatus.COMPLETED,
    ) -> TraceRecord:
        trace = self.get_trace(tenant_id, trace_id)
        updated = trace.model_copy(
            update={"status": TraceStatus(status), "ended_at": datetime.now(UTC)}
        )
        self._traces[updated.trace_id] = updated
        return updated

    def start_span(
        self,
        *,
        trace_id: str,
        name: str,
        attributes: dict | None = None,
    ) -> SpanRecord:
        if trace_id not in self._traces:
            raise TraceNotFoundError(f"Trace not found: {trace_id}")
        span = SpanRecord(trace_id=trace_id, name=name, attributes=attributes or {})
        self._spans[span.span_id] = span
        return span

    def finish_span(
        self,
        span_id: UUID | str,
        status: SpanStatus | str = SpanStatus.COMPLETED,
        error: str | None = None,
    ) -> SpanRecord:
        span_uuid = span_id if isinstance(span_id, UUID) else UUID(span_id)
        span = self._spans.get(span_uuid)
        if span is None:
            raise SpanNotFoundError(f"Span not found: {span_id}")
        updated = span.model_copy(
            update={"status": SpanStatus(status), "ended_at": datetime.now(UTC), "error": error}
        )
        self._spans[updated.span_id] = updated
        return updated

    def get_trace(self, tenant_id: str, trace_id: str) -> TraceRecord:
        trace = self._traces.get(trace_id)
        if trace is None or trace.tenant_id != tenant_id:
            raise TraceNotFoundError(f"Trace not found: {trace_id}")
        return trace

    def list_traces(self, tenant_id: str) -> list[TraceRecord]:
        return sorted(
            [trace for trace in self._traces.values() if trace.tenant_id == tenant_id],
            key=lambda trace: trace.started_at,
        )

    def list_spans(self, trace_id: str) -> list[SpanRecord]:
        return sorted(
            [span for span in self._spans.values() if span.trace_id == trace_id],
            key=lambda span: span.started_at,
        )

    def trace_counts(self, tenant_id: str) -> tuple[int, int]:
        traces = self.list_traces(tenant_id)
        open_traces = sum(trace.status == TraceStatus.RUNNING for trace in traces)
        completed_traces = sum(trace.status == TraceStatus.COMPLETED for trace in traces)
        return open_traces, completed_traces
