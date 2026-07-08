from constants import PieceType, Color
from Piece import Piece
from interfaces import IBoard
from move_validator import MoveValidator

class Board(IBoard):
    def __init__(self, grid_strings):
        num_rows = len(grid_strings)
        self.grid = [
            [self._parse_piece(cell, r, num_rows) for cell in row]
            for r, row in enumerate(grid_strings)
        ]
        self._validator = MoveValidator(self)

    def _parse_piece(self, piece_str, row, num_rows):
        if piece_str == '.':
            return None
        color = Color(piece_str[0])
        ptype = PieceType(piece_str[1])
        promotion_row = 0 if color == Color.WHITE else num_rows - 1
        return Piece(color, ptype, start_row=row, promotion_row=promotion_row)

    def get_piece(self, row, col):
        return self.grid[row][col]

    def rows(self):
        return len(self.grid)

    def cols(self):
        return len(self.grid[0])

    def move_piece(self, start, end):
        r1, c1 = start
        r2, c2 = end
        self.grid[r2][c2] = self.grid[r1][c1]
        self.grid[r1][c1] = None

    def remove_piece(self, row, col):
        self.grid[row][col] = None

    def print_board(self):
        for row in self.grid:
            print(" ".join(str(cell) if cell else '.' for cell in row))

    def is_legal(self, start, end, piece, pending_starts=()):
        return self._validator.is_legal(start, end, piece, pending_starts)

    def is_path_clear(self, start, end, pending_starts=()):
        return self._validator._is_path_clear(start, end, pending_starts)
