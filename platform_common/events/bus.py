from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4


@dataclass(frozen=True)
class PublishedEvent:
    event_id: UUID = field(default_factory=uuid4)
    topic: str = "default"
    payload: dict = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EventPublisher(Protocol):
    def publish(self, topic: str, payload: dict) -> PublishedEvent:
        raise NotImplementedError


class InMemoryEventBus:
    def __init__(self) -> None:
        self.events: list[PublishedEvent] = []

    def publish(self, topic: str, payload: dict) -> PublishedEvent:
        event = PublishedEvent(topic=topic, payload=payload)
        self.events.append(event)
        return event

    def list_events(self, topic: str | None = None) -> list[PublishedEvent]:
        return [event for event in self.events if topic is None or event.topic == topic]
