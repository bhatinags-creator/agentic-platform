from platform_common.events.envelope import ActorType, ErrorEnvelope, EventEnvelope


def test_event_envelope_factory() -> None:
    event = EventEnvelope.create(
        event_type="AgentRunStarted",
        tenant_id="tenant-a",
        trace_id="trace-1",
        correlation_id="corr-1",
        actor_type=ActorType.USER,
        actor_id="user-1",
        subject_type="agent_run",
        subject_id="run-1",
        payload={"agent_id": "agent.credit-risk-supervisor"},
        idempotency_key="idem-1",
    )
    assert event.actor.type == ActorType.USER
    assert event.subject.type == "agent_run"
    assert event.payload["agent_id"] == "agent.credit-risk-supervisor"
    assert event.schema_version == "1.0"


def test_error_envelope_contract() -> None:
    error = ErrorEnvelope(code="POLICY_DENIED", message="Tool access denied", trace_id="trace-1")
    assert error.retryable is False
    assert error.details == {}
