from abc import ABC, abstractmethod


class MoveStrategy(ABC):
    @abstractmethod
    def is_legal(self, start, end, target) -> bool:
        pass

    def requires_clear_path(self) -> bool:
        return True


class KingStrategy(MoveStrategy):
    def is_legal(self, start, end, target) -> bool:
        dr, dc = abs(start.row - end.row), abs(start.col - end.col)
        return dr <= 1 and dc <= 1 and (dr, dc) != (0, 0)

    def requires_clear_path(self) -> bool:
        return False


class RookStrategy(MoveStrategy):
    def is_legal(self, start, end, target) -> bool:
        return start.row == end.row or start.col == end.col


class BishopStrategy(MoveStrategy):
    def is_legal(self, start, end, target) -> bool:
        return abs(start.row - end.row) == abs(start.col - end.col)


class QueenStrategy(MoveStrategy):
    def is_legal(self, start, end, target) -> bool:
        return (
            start.row == end.row
            or start.col == end.col
            or abs(start.row - end.row) == abs(start.col - end.col)
        )


class KnightStrategy(MoveStrategy):
    def is_legal(self, start, end, target) -> bool:
        dr, dc = abs(start.row - end.row), abs(start.col - end.col)
        return (dr == 2 and dc == 1) or (dr == 1 and dc == 2)

    def requires_clear_path(self) -> bool:
        return False


class PawnStrategy(MoveStrategy):
    def __init__(self, color, start_row=None, promotion_row=None):
        from kungfu_chess.shared.constants import Color
        self.direction = -1 if color == Color.WHITE else 1
        self.start_row = start_row
        self.promotion_row = promotion_row
        self._color = color

    def is_legal(self, start, end, target) -> bool:
        dc = abs(start.col - end.col)
        dr = end.row - start.row
        # Forward one step (no capture)
        if dc == 0 and dr == self.direction:
            return target is None
        # Forward two steps from starting row (no capture)
        if dc == 0 and dr == 2 * self.direction and start.row == self.start_row:
            return target is None
        # Diagonal capture
        if dc == 1 and dr == self.direction:
            return target is not None and target.color != self._color
        return False

    def requires_clear_path(self) -> bool:
        return True
