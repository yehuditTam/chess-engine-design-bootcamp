from dataclasses import dataclass
from typing import Optional, Tuple
from kungfu_chess.shared.constants import PieceType, Color, PieceState


# frozen=True enforces immutability so view and tests can never accidentally mutate game state
# through a snapshot reference.
@dataclass(frozen=True)
class PieceSnapshot:
    color: Color
    ptype: PieceType
    is_cooling: bool = False
    state: PieceState = PieceState.IDLE
    is_airborne: bool = False


@dataclass(frozen=True)
class BoardSnapshot:
    grid: tuple
    rows: int
    cols: int

    def get(self, row, col) -> Optional[PieceSnapshot]:
        return self.grid[row][col]


@dataclass(frozen=True)
class MoveResult:
    ok: bool
    reason: str = ""


@dataclass(frozen=True)
class PlayerSnapshot:
    name: str
    color: Color
    score: int
    moves: Tuple  # tuple of (time_str, move_str)
    captured: Tuple = ()  # tuple of PieceType


@dataclass(frozen=True)
class GameSnapshot:
    board: BoardSnapshot
    black: PlayerSnapshot
    white: PlayerSnapshot
