import pytest

from app.core.events.bus import EventBus, Publisher, Subscriber
from app.core.events.models import Event, EventType


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.mark.asyncio
async def test_event_publishing_and_subscribing(event_bus: EventBus):
    received_events = []

    async def callback(event: Event):
        received_events.append(event)

    event_bus.subscribe(EventType.WORKFLOW_CREATED, callback)

    event = Event(
        event_type=EventType.WORKFLOW_CREATED,
        source_component="test_publisher",
        payload={"message": "hello"},
    )

    await event_bus.publish(event)

    assert len(received_events) == 1
    assert received_events[0].id == event.id
    assert received_events[0].payload["message"] == "hello"


@pytest.mark.asyncio
async def test_multiple_subscribers(event_bus: EventBus):
    received_1 = []
    received_2 = []

    async def callback1(event: Event):
        received_1.append(event)

    async def callback2(event: Event):
        received_2.append(event)

    event_bus.subscribe(EventType.TASK_STARTED, callback1)
    event_bus.subscribe(EventType.TASK_STARTED, callback2)

    event = Event(
        event_type=EventType.TASK_STARTED,
        source_component="test",
    )

    await event_bus.publish(event)

    assert len(received_1) == 1
    assert len(received_2) == 1


@pytest.mark.asyncio
async def test_global_subscriber(event_bus: EventBus):
    received_events = []

    async def global_callback(event: Event):
        received_events.append(event)

    event_bus.subscribe_all(global_callback)

    event1 = Event(event_type=EventType.WORKFLOW_CREATED, source_component="test")
    event2 = Event(event_type=EventType.TASK_STARTED, source_component="test")

    await event_bus.publish(event1)
    await event_bus.publish(event2)

    assert len(received_events) == 2
    assert received_events[0].event_type == EventType.WORKFLOW_CREATED
    assert received_events[1].event_type == EventType.TASK_STARTED


@pytest.mark.asyncio
async def test_error_in_subscriber_does_not_crash_bus(event_bus: EventBus, caplog):
    received_events = []

    async def failing_callback(event: Event):
        raise ValueError("Simulated failure")

    async def successful_callback(event: Event):
        received_events.append(event)

    event_bus.subscribe(EventType.WORKFLOW_CANCELLED, failing_callback)
    event_bus.subscribe(EventType.WORKFLOW_CANCELLED, successful_callback)

    event = Event(event_type=EventType.WORKFLOW_CANCELLED, source_component="test")

    await event_bus.publish(event)

    # The successful callback should still run despite the failing one
    assert len(received_events) == 1
    # Check that error was logged
    assert "Error executing event subscriber" in caplog.text


@pytest.mark.asyncio
async def test_publisher_and_subscriber_classes(event_bus: EventBus):
    class MyPublisher(Publisher):
        pass

    class MySubscriber(Subscriber):
        def __init__(self, bus: EventBus):
            super().__init__(bus)
            self.received = []

        async def handle_event(self, event: Event):
            self.received.append(event)

    pub = MyPublisher(event_bus)
    sub = MySubscriber(event_bus)

    sub.subscribe(EventType.TOOL_LOADED, sub.handle_event)

    event = Event(event_type=EventType.TOOL_LOADED, source_component="pub")
    await pub.publish_event(event)

    assert len(sub.received) == 1
    assert sub.received[0].event_type == EventType.TOOL_LOADED
