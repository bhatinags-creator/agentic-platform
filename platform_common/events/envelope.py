from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ActorType(StrEnum):
    USER = "user"
    AGENT = "agent"
    SERVICE = "service"
    SYSTEM = "system"


class Actor(BaseModel):
    type: ActorType
    id: str = Field(min_length=1)


class Subject(BaseModel):
    type: str = Field(min_length=1)
    id: str = Field(min_length=1)


class EventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    actor: Actor
    subject: Subject
    payload: dict[str, Any] = Field(default_factory=dict)
    schema_version: str = "1.0"
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    idempotency_key: str | None = None

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        tenant_id: str,
        trace_id: str,
        correlation_id: str,
        actor_type: ActorType,
        actor_id: str,
        subject_type: str,
        subject_id: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> "EventEnvelope":
        return cls(
            event_type=event_type,
            tenant_id=tenant_id,
            trace_id=trace_id,
            correlation_id=correlation_id,
            actor=Actor(type=actor_type, id=actor_id),
            subject=Subject(type=subject_type, id=subject_id),
            payload=payload or {},
            idempotency_key=idempotency_key,
        )


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    retryable: bool = False
    trace_id: str
    policy_decision_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
