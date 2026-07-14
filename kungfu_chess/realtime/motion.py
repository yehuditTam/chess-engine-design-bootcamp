from dataclasses import dataclass
from kungfu_chess.model.position import Position


@dataclass
class PendingMove:
    start: Position
    end: Position
    arrive_at: float


@dataclass
class PendingJump:
    cell: Position
    land_at: float


@dataclass
class PendingCooldown:
    cell: Position
    ready_at: float
