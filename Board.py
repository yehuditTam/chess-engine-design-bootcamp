from constants import PieceType, Color, TILE_SIZE
from Piece import Piece
from interfaces import IBoard
from exceptions import OutOfBoundsError, BlockedPathError, FriendlyFireError, InvalidMoveError

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

    def print_board(self):
        for row in self.grid:
            print(" ".join(str(cell) if cell else '.' for cell in row))

    def is_legal(self, start, end, piece, pending_starts=()):
        r2, c2 = end
        if not (0 <= r2 < self.rows() and 0 <= c2 < self.cols()):
            raise OutOfBoundsError(f"Target {end} is out of bounds")
        target = self.grid[r2][c2]
        if not piece.is_legal_move(start, end, target):
            raise InvalidMoveError(f"Illegal move for {piece} from {start} to {end}")
        if piece.requires_clear_path():
            if not self.is_path_clear(start, end, pending_starts):
                raise BlockedPathError(f"Path from {start} to {end} is blocked")
        if target is not None and target.color == piece.color:
            raise FriendlyFireError(f"Cannot capture own piece at {end}")
        return True

    def is_path_clear(self, start, end, pending_starts=()):
        dr, dc = self._direction(start, end)
        curr_r, curr_c = start[0] + dr, start[1] + dc
        while (curr_r, curr_c) != end:
            if self.grid[curr_r][curr_c] is not None and (curr_r, curr_c) not in pending_starts:
                return False
            curr_r += dr
            curr_c += dc
        return True

    def _direction(self, start, end):
        r1, c1 = start
        r2, c2 = end
        dr = 0 if r1 == r2 else (1 if r2 > r1 else -1)
        dc = 0 if c1 == c2 else (1 if c2 > c1 else -1)
        return dr, dc
