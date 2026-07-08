from abc import ABC, abstractmethod


class MoveStrategy(ABC):
    @abstractmethod
    def is_legal(self, start, end, target) -> bool:
        pass

    def requires_clear_path(self) -> bool:
        return False


class KingStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        r1, c1 = start
        r2, c2 = end
        dr, dc = abs(r1 - r2), abs(c1 - c2)
        return (dr <= 1 and dc <= 1) and (dr, dc) != (0, 0)


class RookStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        r1, c1 = start
        r2, c2 = end
        return r1 == r2 or c1 == c2

    def requires_clear_path(self):
        return True


class BishopStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        r1, c1 = start
        r2, c2 = end
        return abs(r1 - r2) == abs(c1 - c2)

    def requires_clear_path(self):
        return True


class QueenStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        r1, c1 = start
        r2, c2 = end
        return r1 == r2 or c1 == c2 or abs(r1 - r2) == abs(c1 - c2)

    def requires_clear_path(self):
        return True


class KnightStrategy(MoveStrategy):
    def is_legal(self, start, end, target):
        r1, c1 = start
        r2, c2 = end
        dr, dc = abs(r1 - r2), abs(c1 - c2)
        return (dr == 2 and dc == 1) or (dr == 1 and dc == 2)


class PawnStrategy(MoveStrategy):
    def __init__(self, color, start_row=None, promotion_row=None):
        from constants import Color
        self.color = color
        self.direction = -1 if color == Color.WHITE else 1
        self.start_row = start_row
        self.promotion_row = promotion_row

    def is_legal(self, start, end, target):
        r1, c1 = start
        r2, c2 = end
        dc = abs(c1 - c2)
        dr = r2 - r1
        if dc == 0 and dr == self.direction:
            return target is None
        if (dc == 0 and dr == 2 * self.direction
                and self.start_row is not None and r1 == self.start_row
                and self.promotion_row is not None and r2 != self.promotion_row):
            return target is None
        if dc == 1 and dr == self.direction:
            return target is not None and target.color != self.color
        return False

    def requires_clear_path(self):
        return True
