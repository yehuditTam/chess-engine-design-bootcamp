from abc import ABC, abstractmethod
from kungfu_chess.model.position import Position


class MoveStrategy(ABC):
    @abstractmethod
    def is_legal(self, start: Position, end: Position, target) -> bool:
        pass

    def requires_clear_path(self) -> bool:
        return False


class KingStrategy(MoveStrategy):
    def is_legal(self, start: Position, end: Position, target):
        dr, dc = abs(start.row - end.row), abs(start.col - end.col)
        return (dr <= 1 and dc <= 1) and (dr, dc) != (0, 0)


class RookStrategy(MoveStrategy):
    def is_legal(self, start: Position, end: Position, target):
        return start.row == end.row or start.col == end.col

    def requires_clear_path(self):
        return True


class BishopStrategy(MoveStrategy):
    def is_legal(self, start: Position, end: Position, target):
        return abs(start.row - end.row) == abs(start.col - end.col)

    def requires_clear_path(self):
        return True


class QueenStrategy(MoveStrategy):
    def is_legal(self, start: Position, end: Position, target):
        return (start.row == end.row or start.col == end.col or
                abs(start.row - end.row) == abs(start.col - end.col))

    def requires_clear_path(self):
        return True


class KnightStrategy(MoveStrategy):
    def is_legal(self, start: Position, end: Position, target):
        dr, dc = abs(start.row - end.row), abs(start.col - end.col)
        return (dr == 2 and dc == 1) or (dr == 1 and dc == 2)


class PawnStrategy(MoveStrategy):
    def __init__(self, color, start_row=None, promotion_row=None):
        from kungfu_chess.shared.constants import Color
        self.color = color
        self.direction = -1 if color == Color.WHITE else 1
        self.start_row = start_row
        self.promotion_row = promotion_row

    def is_legal(self, start: Position, end: Position, target):
        dc = abs(start.col - end.col)
        dr = end.row - start.row
        if dc == 0 and dr == self.direction:
            return target is None
        if (dc == 0 and dr == 2 * self.direction
                and self.start_row is not None and start.row == self.start_row
                and self.promotion_row is not None and end.row != self.promotion_row):
            return target is None
        if dc == 1 and dr == self.direction:
            return target is not None and target.color != self.color
        return False

    def requires_clear_path(self):
        return True
