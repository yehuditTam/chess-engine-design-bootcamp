from kungfu_chess.shared.constants import PieceType, Color
from kungfu_chess.model.piece import Piece
from kungfu_chess.rules.piece_rules import make_strategy
from kungfu_chess.shared.interfaces import IBoard
from kungfu_chess.shared.exceptions import InvalidMoveError


class Board(IBoard):
    def __init__(self, grid_strings):
        num_rows = len(grid_strings)
        self.grid = [
            [self._parse_piece(cell, r, num_rows) for cell in row]
            for r, row in enumerate(grid_strings)
        ]

    def _parse_piece(self, token: str, row: int, num_rows: int) -> Piece | None:
        """Converts a board token like 'wK' into a Piece with the correct strategy."""
        if token == ".":
            return None
        color = Color(token[0])
        ptype = PieceType(token[1])
        promo_row = 0 if color == Color.WHITE else num_rows - 1
        start_row = num_rows - 2 if color == Color.WHITE else 1
        strategy = make_strategy(ptype, color, start_row, promo_row)
        return Piece(color, ptype, move_strategy=strategy)

    def get_piece(self, row: int, col: int) -> Piece | None:
        return self.grid[row][col]

    def rows(self) -> int:
        return len(self.grid)

    def cols(self) -> int:
        return len(self.grid[0])

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows() and 0 <= col < self.cols()

    def add_piece(self, row: int, col: int, piece: Piece) -> None:
        if self.grid[row][col] is not None:
            raise InvalidMoveError(f"Cell ({row}, {col}) is already occupied")
        self.grid[row][col] = piece

    def move_piece(self, start, end) -> None:
        r1, c1 = start
        r2, c2 = end
        self.grid[r2][c2] = self.grid[r1][c1]
        self.grid[r1][c1] = None

    def remove_piece(self, row: int, col: int) -> None:
        self.grid[row][col] = None
