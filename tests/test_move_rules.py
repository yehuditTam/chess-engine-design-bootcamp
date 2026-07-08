import pytest
from move_rules import KingStrategy, RookStrategy, BishopStrategy, QueenStrategy, KnightStrategy, PawnStrategy
from constants import Color, PieceType
from Piece import Piece

EMPTY_TARGET = None


def make_piece(color, ptype):
    return Piece(color, ptype)


class TestKingStrategy:
    s = KingStrategy()

    def test_one_step_any_direction(self):
        for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            assert self.s.is_legal((4,4), (4+dr, 4+dc), EMPTY_TARGET)

    def test_two_steps_illegal(self):
        assert not self.s.is_legal((4,4), (4,6), EMPTY_TARGET)
        assert not self.s.is_legal((4,4), (6,4), EMPTY_TARGET)

    def test_no_move_illegal(self):
        assert not self.s.is_legal((4,4), (4,4), EMPTY_TARGET)


class TestRookStrategy:
    s = RookStrategy()

    def test_horizontal(self):
        assert self.s.is_legal((3,0), (3,7), EMPTY_TARGET)

    def test_vertical(self):
        assert self.s.is_legal((0,3), (7,3), EMPTY_TARGET)

    def test_diagonal_illegal(self):
        assert not self.s.is_legal((0,0), (3,3), EMPTY_TARGET)


class TestBishopStrategy:
    s = BishopStrategy()

    def test_diagonal(self):
        assert self.s.is_legal((0,0), (5,5), EMPTY_TARGET)
        assert self.s.is_legal((5,5), (2,2), EMPTY_TARGET)

    def test_straight_illegal(self):
        assert not self.s.is_legal((0,0), (0,5), EMPTY_TARGET)
        assert not self.s.is_legal((0,0), (5,0), EMPTY_TARGET)


class TestQueenStrategy:
    s = QueenStrategy()

    def test_straight(self):
        assert self.s.is_legal((3,3), (3,7), EMPTY_TARGET)
        assert self.s.is_legal((3,3), (7,3), EMPTY_TARGET)

    def test_diagonal(self):
        assert self.s.is_legal((3,3), (6,6), EMPTY_TARGET)

    def test_L_shape_illegal(self):
        assert not self.s.is_legal((3,3), (5,4), EMPTY_TARGET)


class TestKnightStrategy:
    s = KnightStrategy()

    def test_all_L_shapes(self):
        for dr, dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            assert self.s.is_legal((4,4), (4+dr, 4+dc), EMPTY_TARGET)

    def test_straight_illegal(self):
        assert not self.s.is_legal((4,4), (4,5), EMPTY_TARGET)

    def test_diagonal_illegal(self):
        assert not self.s.is_legal((4,4), (5,5), EMPTY_TARGET)


class TestPawnStrategy:
    def test_white_moves_up(self):
        s = PawnStrategy(Color.WHITE)
        assert s.is_legal((4,4), (3,4), None)

    def test_black_moves_down(self):
        s = PawnStrategy(Color.BLACK)
        assert s.is_legal((3,4), (4,4), None)

    def test_white_cannot_move_down(self):
        s = PawnStrategy(Color.WHITE)
        assert not s.is_legal((4,4), (5,4), None)

    def test_pawn_blocked_by_piece(self):
        s = PawnStrategy(Color.WHITE)
        blocker = make_piece(Color.BLACK, PieceType.PAWN)
        assert not s.is_legal((4,4), (3,4), blocker)

    def test_pawn_capture_diagonal(self):
        s = PawnStrategy(Color.WHITE)
        enemy = make_piece(Color.BLACK, PieceType.PAWN)
        assert s.is_legal((4,4), (3,5), enemy)

    def test_pawn_cannot_capture_empty(self):
        s = PawnStrategy(Color.WHITE)
        assert not s.is_legal((4,4), (3,5), None)

    def test_pawn_cannot_capture_own_color(self):
        s = PawnStrategy(Color.WHITE)
        friendly = make_piece(Color.WHITE, PieceType.PAWN)
        assert not s.is_legal((4,4), (3,5), friendly)
