from dataclasses import dataclass
from kungfu_chess.shared.constants import PieceType, Color, PieceState

# frozen=True enforces immutability — view and tests can never accidentally mutate game state.


@dataclass(frozen=True)
class PieceSnapshot:
    color: Color
    ptype: PieceType
    state: PieceState = PieceState.IDLE
    cooldown_ends_at: float = 0.0
    cooldown_started_at: float = 0.0
    jump_started_at: float = 0.0


@dataclass(frozen=True)
class BoardSnapshot:
    grid: tuple
    rows: int
    cols: int

    def get(self, row: int, col: int) -> PieceSnapshot | None:
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
    moves: tuple
    captured: tuple = ()


@dataclass(frozen=True)
class GameSnapshot:
    board: BoardSnapshot
    black: PlayerSnapshot
    white: PlayerSnapshot
    game_over: bool = False
