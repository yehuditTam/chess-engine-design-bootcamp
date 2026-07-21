from enum import Enum, auto
from collections import defaultdict
from typing import Callable


class EventType(Enum):
    PIECE_MOVED    = auto()
    PIECE_CAPTURED = auto()
    PIECE_JUMPED   = auto()
    GAME_OVER      = auto()
    GAME_STARTED   = auto()
    SCORE_UPDATED  = auto()
    MOVE_LOGGED    = auto()


class EventBus:
    """Synchronous publish/subscribe bus. All callbacks are invoked immediately on publish."""

    def __init__(self):
        self._subscribers: dict[EventType, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        self._subscribers[event_type].append(callback)

    def publish(self, event_type: EventType, **data) -> None:
        for cb in self._subscribers[event_type]:
            cb(**data)

    def clear(self) -> None:
        """Remove all subscriptions — call before restarting a game on the same bus."""
        self._subscribers.clear()
