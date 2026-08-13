import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable, Dict, List, Optional

from app.core.events.models import Event, EventType

logger = logging.getLogger(__name__)

EventCallback = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    Centralized lightweight in-memory Event Bus for the runtime components.
    Allows publishing and subscribing to events asynchronously.
    """

    def __init__(self) -> None:
        # Map event types to a list of subscriber callbacks
        self._subscribers: Dict[str, List[EventCallback]] = defaultdict(list)
        self._global_subscribers: List[EventCallback] = []

    def subscribe(self, event_type: EventType | str, callback: EventCallback) -> None:
        """
        Subscribe a callback to a specific event type.
        """
        event_name = (
            event_type.value if isinstance(event_type, EventType) else event_type
        )
        if callback not in self._subscribers[event_name]:
            self._subscribers[event_name].append(callback)
            logger.debug(f"Subscribed to {event_name}")

    def subscribe_all(self, callback: EventCallback) -> None:
        """
        Subscribe a callback to all events (useful for logging/monitoring).
        """
        if callback not in self._global_subscribers:
            self._global_subscribers.append(callback)
            logger.debug("Subscribed to all events")

    def unsubscribe(self, event_type: EventType | str, callback: EventCallback) -> None:
        """
        Unsubscribe a callback from a specific event type.
        """
        event_name = (
            event_type.value if isinstance(event_type, EventType) else event_type
        )
        if callback in self._subscribers[event_name]:
            self._subscribers[event_name].remove(callback)
            logger.debug(f"Unsubscribed from {event_name}")

    def unsubscribe_all(self, callback: EventCallback) -> None:
        """
        Unsubscribe a callback from global events.
        """
        if callback in self._global_subscribers:
            self._global_subscribers.remove(callback)
            logger.debug("Unsubscribed from all events")

    async def publish(self, event: Event) -> None:
        """
        Publish an event to the Event Bus asynchronously.
        Routes the event to all registered subscribers.
        """
        event_name = (
            event.event_type.value
            if isinstance(event.event_type, EventType)
            else event.event_type
        )
        callbacks = self._subscribers.get(event_name, []) + self._global_subscribers

        if not callbacks:
            logger.debug(f"No subscribers for event: {event_name}")
            return

        # Execute callbacks concurrently
        tasks = [
            asyncio.create_task(self._safe_execute(callback, event))
            for callback in callbacks
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_execute(self, callback: EventCallback, event: Event) -> None:
        """
        Executes a subscriber callback safely, catching any exceptions to prevent
        crashing the Event Bus.
        """
        try:
            await callback(event)
        except Exception as e:
            logger.error(
                f"Error executing event subscriber for event {event.event_type}: {e}",
                exc_info=True,
            )


class Publisher:
    """
    Base class or mixin for components that publish events.
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    async def publish_event(self, event: Event) -> None:
        """
        Publishes the given event to the configured event bus.
        """
        await self.event_bus.publish(event)


class Subscriber:
    """
    Base class or mixin for components that subscribe to events.
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def subscribe(self, event_type: EventType | str, callback: EventCallback) -> None:
        """
        Subscribes a callback to a specific event type on the configured event bus.
        """
        self.event_bus.subscribe(event_type, callback)

    def subscribe_all(self, callback: EventCallback) -> None:
        """
        Subscribes a callback to all events on the configured event bus.
        """
        self.event_bus.subscribe_all(callback)


_event_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Returns the global singleton EventBus instance.
    """
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus()
    return _event_bus_instance
