from enum import Enum, auto
from collections import defaultdict
from typing import Callable


class EventType(Enum):
    PIECE_MOVED = auto()
    PIECE_CAPTURED = auto()
    PIECE_JUMPED = auto()
    GAME_OVER = auto()


class EventBus:
    """Synchronous pub/sub bus.

    Subscribers register a callable per EventType.
    Publishers call publish() and all registered callbacks are invoked immediately.
    Thread-safety is intentionally out of scope for this single-process stage.
    """

    def __init__(self):
        self._subscribers: dict[EventType, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """Register *callback* to be called whenever *event_type* is published."""
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: EventType, **data) -> None:
        """Invoke all callbacks registered for *event_type*, passing **data as kwargs."""
        for cb in self._subscribers[event_type]:
            cb(**data)
