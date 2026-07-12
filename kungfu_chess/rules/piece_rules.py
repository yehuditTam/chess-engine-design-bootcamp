from abc import ABC, abstractmethod
from kungfu_chess.model.position import Position

# Design Pattern: Strategy
# Each piece type encapsulates its own movement rule as a separate strategy class.
# This allows GameEngine and RuleEngine to validate any move without knowing
# which piece type they are dealing with — they just call is_legal().
# Adding a new piece type means adding a new strategy class, not modifying existing code.


class MoveStrategy(ABC):
    """Abstract base for all piece movement strategies."""

    @abstractmethod
    def is_legal(self, start, end, target) -> bool:
        pass

    def requires_clear_path(self) -> bool:
        # Most pieces need a clear path (rook, bishop, queen, pawn).
        # Knight overrides this to return False — it jumps over pieces.
        return False


class KingStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        dr, dc = abs(start.row - end.row), abs(start.col - end.col)
        return (dr <= 1 and dc <= 1) and (dr, dc) != (0, 0)


class RookStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        return start.row == end.row or start.col == end.col

    def requires_clear_path(self):
        return True


class BishopStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        return abs(start.row - end.row) == abs(start.col - end.col)

    def requires_clear_path(self):
        return True


class QueenStrategy(MoveStrategy):
    # Queen combines rook and bishop movement — no separate logic needed.
    def is_legal(self, start, end, target):
        return (start.row == end.row or start.col == end.col or
                abs(start.row - end.row) == abs(start.col - end.col))

    def requires_clear_path(self):
        return True


class KnightStrategy(MoveStrategy):
    # Knight is the only piece that jumps — requires_clear_path() stays False.
    def is_legal(self, start, end, target):
        dr, dc = abs(start.row - end.row), abs(start.col - end.col)
        return (dr == 2 and dc == 1) or (dr == 1 and dc == 2)


class PawnStrategy(MoveStrategy):
    # Pawn is the most stateful strategy: direction depends on color,
    # double-move is only allowed from the start row, and capture is diagonal only.
    # start_row and promotion_row are injected at construction time from Board.
    def __init__(self, color, start_row=None, promotion_row=None):
        from kungfu_chess.shared.constants import Color
        self.color = color
        self.direction = -1 if color == Color.WHITE else 1
        self.start_row = start_row
        self.promotion_row = promotion_row

    def is_legal(self, start, end, target):
        dc = abs(start.col - end.col)
        dr = end.row - start.row
        if dc == 0 and dr == self.direction:
            return target is None
        if (dc == 0 and dr == 2 * self.direction
                and self.start_row is not None and start.row == self.start_row):
            return target is None
        if dc == 1 and dr == self.direction:
            return target is not None and target.color != self.color
        return False

    def requires_clear_path(self):
        return True
