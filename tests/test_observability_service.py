from observability.service import ObservabilityService, SpanStatus, TraceStatus


def test_observability_service_records_trace_and_spans() -> None:
    service = ObservabilityService()
    trace = service.start_trace(tenant_id="tenant-a", run_id="run-1", agent_id="agent.support")
    span = service.start_span(trace_id=trace.trace_id, name="model_invocation")

    finished_span = service.finish_span(span.span_id)
    finished_trace = service.finish_trace("tenant-a", trace.trace_id)

    assert finished_span.status == SpanStatus.COMPLETED
    assert finished_span.ended_at is not None
    assert finished_trace.status == TraceStatus.COMPLETED
    assert service.list_spans(trace.trace_id) == [finished_span]
    assert service.trace_counts("tenant-a") == (0, 1)
