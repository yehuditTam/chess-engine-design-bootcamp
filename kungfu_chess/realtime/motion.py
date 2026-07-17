from dataclasses import dataclass
from kungfu_chess.model.position import Position

# Plain dataclasses (not frozen) so RealTimeArbiter and tests can mutate arrive_at/land_at
# directly to simulate elapsed time without a fake clock.


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
