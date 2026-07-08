from exceptions import OutOfBoundsError, BlockedPathError, FriendlyFireError, InvalidMoveError


class MoveValidator:
    def __init__(self, board):
        self._board = board

    def is_legal(self, start, end, piece, pending_starts=()):
        r2, c2 = end
        if not (0 <= r2 < self._board.rows() and 0 <= c2 < self._board.cols()):
            raise OutOfBoundsError(f"Target {end} is out of bounds")
        target = self._board.get_piece(r2, c2)
        if not piece.is_legal_move(start, end, target):
            raise InvalidMoveError(f"Illegal move for {piece} from {start} to {end}")
        if piece.requires_clear_path() and not self._is_path_clear(start, end, pending_starts):
            raise BlockedPathError(f"Path from {start} to {end} is blocked")
        if target is not None and target.color == piece.color:
            raise FriendlyFireError(f"Cannot capture own piece at {end}")
        return True

    def _is_path_clear(self, start, end, pending_starts=()):
        dr, dc = self._direction(start, end)
        curr_r, curr_c = start[0] + dr, start[1] + dc
        while (curr_r, curr_c) != end:
            if self._board.get_piece(curr_r, curr_c) is not None and (curr_r, curr_c) not in pending_starts:
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
