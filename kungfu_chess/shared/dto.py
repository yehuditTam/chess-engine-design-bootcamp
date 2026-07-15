from dataclasses import dataclass
from typing import Optional, List
from kungfu_chess.shared.constants import PieceType, Color, PieceState


@dataclass(frozen=True)
class PieceSnapshot:
    color: Color
    ptype: PieceType
    is_cooling: bool = False
    state: PieceState = PieceState.IDLE
    is_airborne: bool = False


@dataclass(frozen=True)
class BoardSnapshot:
    grid: tuple  # tuple of tuples of Optional[PieceSnapshot]
    rows: int
    cols: int

    def get(self, row, col) -> Optional[PieceSnapshot]:
        return self.grid[row][col]


@dataclass(frozen=True)
class MoveResult:
    ok: bool
    reason: str = ""
