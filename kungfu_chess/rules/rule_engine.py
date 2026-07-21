from kungfu_chess.model.position import Position
from kungfu_chess.shared.exceptions import (
    OutOfBoundsError, BlockedPathError, FriendlyFireError, InvalidMoveError
)


class RuleEngine:
    """Read-only validator. Never mutates the board."""

    def __init__(self, board):
        self._board = board

    def is_legal(self, start: Position, end: Position, piece, pending_starts=()) -> bool:
        """Raises an exception if the move is illegal, returns True otherwise."""
        if not (0 <= end.row < self._board.rows() and 0 <= end.col < self._board.cols()):
            raise OutOfBoundsError(f"Target {end} is out of bounds")
        target = self._board.get_piece(*end)
        if not piece.is_legal_move(start, end, target):
            raise InvalidMoveError(f"Illegal move for {piece} from {start} to {end}")
        if piece.requires_clear_path() and not self._is_path_clear(start, end, pending_starts):
            raise BlockedPathError(f"Path from {start} to {end} is blocked")
        if target is not None and target.color == piece.color:
            raise FriendlyFireError(f"Cannot capture own piece at {end}")
        return True

    def _is_path_clear(self, start: Position, end: Position, pending_starts=()) -> bool:
        """Returns True if no piece occupies any square between start and end."""
        dr, dc = start.direction_to(end)
        curr = Position(start.row + dr, start.col + dc)
        while curr != end:
            if self._board.get_piece(*curr) is not None and curr not in pending_starts:
                return False
            curr = Position(curr.row + dr, curr.col + dc)
        return True
