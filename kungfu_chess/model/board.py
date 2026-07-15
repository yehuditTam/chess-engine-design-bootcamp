from kungfu_chess.shared.constants import PieceType, Color, PieceState
from kungfu_chess.model.piece import Piece
from kungfu_chess.rules.piece_rules import (
    KingStrategy, RookStrategy, BishopStrategy,
    QueenStrategy, KnightStrategy, PawnStrategy,
)
from kungfu_chess.shared.interfaces import IBoard
from kungfu_chess.shared.dto import PieceSnapshot, BoardSnapshot
from kungfu_chess.shared.exceptions import InvalidMoveError

_STRATEGY_MAP = {
    PieceType.KING:   lambda color, start_row, promotion_row: KingStrategy(),
    PieceType.ROOK:   lambda color, start_row, promotion_row: RookStrategy(),
    PieceType.BISHOP: lambda color, start_row, promotion_row: BishopStrategy(),
    PieceType.QUEEN:  lambda color, start_row, promotion_row: QueenStrategy(),
    PieceType.KNIGHT: lambda color, start_row, promotion_row: KnightStrategy(),
    PieceType.PAWN:   lambda color, start_row, promotion_row: PawnStrategy(color, start_row, promotion_row),
}


class Board(IBoard):
    def __init__(self, grid_strings):
        num_rows = len(grid_strings)
        self.grid = [
            [self._parse_piece(cell, r, num_rows) for cell in row]
            for r, row in enumerate(grid_strings)
        ]

    def _parse_piece(self, piece_str, row, num_rows):
        if piece_str == '.':
            return None
        color = Color(piece_str[0])
        ptype = PieceType(piece_str[1])
        promotion_row = 0 if color == Color.WHITE else num_rows - 1
        start_row = num_rows - 2 if color == Color.WHITE else 1
        strategy = _STRATEGY_MAP[ptype](color, start_row, promotion_row)
        return Piece(color, ptype, move_strategy=strategy)

    def get_piece(self, row, col):
        return self.grid[row][col]

    def rows(self):
        return len(self.grid)

    def cols(self):
        return len(self.grid[0])

    def in_bounds(self, row, col) -> bool:
        return 0 <= row < self.rows() and 0 <= col < self.cols()

    def add_piece(self, row, col, piece):
        if self.grid[row][col] is not None:
            raise InvalidMoveError(f"Cell ({row}, {col}) is already occupied")
        self.grid[row][col] = piece

    def move_piece(self, start, end):
        r1, c1 = start
        r2, c2 = end
        self.grid[r2][c2] = self.grid[r1][c1]
        self.grid[r1][c1] = None

    def remove_piece(self, row, col):
        self.grid[row][col] = None

    def snapshot(self) -> BoardSnapshot:
        grid = tuple(
            tuple(
                PieceSnapshot(p.color, p.ptype, p.state == PieceState.COOLING, p.state)
                if p else None
                for p in row
            )
            for row in self.grid
        )
        return BoardSnapshot(grid=grid, rows=self.rows(), cols=self.cols())
