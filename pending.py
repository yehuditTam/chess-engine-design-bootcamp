from dataclasses import dataclass
from typing import Tuple


@dataclass
class PendingMove:
    start: Tuple[int, int]
    end: Tuple[int, int]
    arrive_at: float


@dataclass
class PendingJump:
    cell: Tuple[int, int]
    land_at: float
