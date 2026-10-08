from platform_common.events.bus import InMemoryEventBus


def test_in_memory_event_bus_publishes_and_filters_events() -> None:
    bus = InMemoryEventBus()

    created = bus.publish("agent.created", {"agent_id": "agent-1"})
    bus.publish("agent.deployed", {"agent_id": "agent-1"})

    assert created.topic == "agent.created"
    assert bus.list_events("agent.created") == [created]
    assert len(bus.list_events()) == 2
