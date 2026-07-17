from abc import ABC, abstractmethod

# Strategy pattern: each piece type owns its movement rule so RuleEngine never needs
# a switch/if-chain on piece type — open/closed principle.


class MoveStrategy(ABC):
    """Abstract base for all piece movement strategies."""

    @abstractmethod
    def is_legal(self, start, end, target) -> bool:
        pass

    def requires_clear_path(self) -> bool:
        # Knight and King don't need path-clearing because they jump or move one step.
        # Overriding here avoids a special-case check in RuleEngine.
        return True


class KingStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        dr, dc = abs(start.row - end.row), abs(start.col - end.col)
        return (dr <= 1 and dc <= 1) and (dr, dc) != (0, 0)

    def requires_clear_path(self):
        return False


class RookStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        return start.row == end.row or start.col == end.col


class BishopStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        return abs(start.row - end.row) == abs(start.col - end.col)


class QueenStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        return (start.row == end.row or start.col == end.col or
                abs(start.row - end.row) == abs(start.col - end.col))


class KnightStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        dr, dc = abs(start.row - end.row), abs(start.col - end.col)
        return (dr == 2 and dc == 1) or (dr == 1 and dc == 2)

    def requires_clear_path(self):
        return False


class PawnStrategy(MoveStrategy):
    # Pawn direction, double-move eligibility, and promotion row are injected at construction
    # so PawnStrategy stays stateless after init — Board owns the row numbers, not the strategy.
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
