from kungfu_chess.rules.piece_rules import (
    KingStrategy, RookStrategy, BishopStrategy, QueenStrategy, KnightStrategy, PawnStrategy
)
from kungfu_chess.shared.constants import Color, PieceType
from kungfu_chess.model.piece import Piece
from kungfu_chess.model.position import Position


def p(r, c):
    return Position(r, c)


def make_piece(color: Color, ptype: PieceType) -> Piece:
    if color not in (Color.WHITE, Color.BLACK):
        raise ValueError(f"Invalid color: {color}")
    if ptype not in PieceType:
        raise ValueError(f"Invalid piece type: {ptype}")
    strategy = PawnStrategy(color) if ptype == PieceType.PAWN else (
        KnightStrategy() if ptype == PieceType.KNIGHT else RookStrategy()
    )
    return Piece(color, ptype, move_strategy=strategy)


class TestKingStrategy:
    s = KingStrategy()

    def test_one_step_any_direction(self):
        for dr, dc in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
            assert self.s.is_legal(p(4, 4), p(4 + dr, 4 + dc), None)

    def test_two_steps_illegal(self):
        assert not self.s.is_legal(p(4, 4), p(4, 6), None)
        assert not self.s.is_legal(p(4, 4), p(6, 4), None)

    def test_no_move_illegal(self):
        assert not self.s.is_legal(p(4, 4), p(4, 4), None)


class TestRookStrategy:
    s = RookStrategy()

    def test_horizontal(self):
        assert self.s.is_legal(p(3, 0), p(3, 7), None)

    def test_vertical(self):
        assert self.s.is_legal(p(0, 3), p(7, 3), None)

    def test_diagonal_illegal(self):
        assert not self.s.is_legal(p(0, 0), p(3, 3), None)


class TestBishopStrategy:
    s = BishopStrategy()

    def test_diagonal(self):
        assert self.s.is_legal(p(0, 0), p(5, 5), None)
        assert self.s.is_legal(p(5, 5), p(2, 2), None)

    def test_straight_illegal(self):
        assert not self.s.is_legal(p(0, 0), p(0, 5), None)
        assert not self.s.is_legal(p(0, 0), p(5, 0), None)


class TestQueenStrategy:
    s = QueenStrategy()

    def test_straight(self):
        assert self.s.is_legal(p(3, 3), p(3, 7), None)
        assert self.s.is_legal(p(3, 3), p(7, 3), None)

    def test_diagonal(self):
        assert self.s.is_legal(p(3, 3), p(6, 6), None)

    def test_L_shape_illegal(self):
        assert not self.s.is_legal(p(3, 3), p(5, 4), None)


class TestKnightStrategy:
    s = KnightStrategy()

    def test_all_L_shapes(self):
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
            assert self.s.is_legal(p(4, 4), p(4 + dr, 4 + dc), None)

    def test_straight_illegal(self):
        assert not self.s.is_legal(p(4, 4), p(4, 5), None)

    def test_diagonal_illegal(self):
        assert not self.s.is_legal(p(4, 4), p(5, 5), None)


class TestPawnStrategy:
    def test_white_moves_up(self):
        s = PawnStrategy(Color.WHITE)
        assert s.is_legal(p(4, 4), p(3, 4), None)

    def test_black_moves_down(self):
        s = PawnStrategy(Color.BLACK)
        assert s.is_legal(p(3, 4), p(4, 4), None)

    def test_white_cannot_move_down(self):
        s = PawnStrategy(Color.WHITE)
        assert not s.is_legal(p(4, 4), p(5, 4), None)

    def test_pawn_blocked_by_piece(self):
        s = PawnStrategy(Color.WHITE)
        blocker = make_piece(Color.BLACK, PieceType.PAWN)
        assert not s.is_legal(p(4, 4), p(3, 4), blocker)

    def test_pawn_capture_diagonal(self):
        s = PawnStrategy(Color.WHITE)
        enemy = make_piece(Color.BLACK, PieceType.PAWN)
        assert s.is_legal(p(4, 4), p(3, 5), enemy)

    def test_pawn_cannot_capture_empty(self):
        s = PawnStrategy(Color.WHITE)
        assert not s.is_legal(p(4, 4), p(3, 5), None)

    def test_pawn_cannot_capture_own_color(self):
        s = PawnStrategy(Color.WHITE)
        friendly = make_piece(Color.WHITE, PieceType.PAWN)
        assert not s.is_legal(p(4, 4), p(3, 5), friendly)

    def test_pawn_double_move_from_start_white(self):
        s = PawnStrategy(Color.WHITE, start_row=6, promotion_row=0)
        assert s.is_legal(p(6, 0), p(4, 0), None)

    def test_pawn_double_move_from_start_black(self):
        s = PawnStrategy(Color.BLACK, start_row=1, promotion_row=7)
        assert s.is_legal(p(1, 0), p(3, 0), None)

    def test_pawn_double_move_not_from_start(self):
        s = PawnStrategy(Color.WHITE, start_row=6, promotion_row=0)
        assert not s.is_legal(p(5, 0), p(3, 0), None)

    def test_pawn_double_move_blocked(self):
        s = PawnStrategy(Color.WHITE, start_row=6, promotion_row=0)
        blocker = make_piece(Color.BLACK, PieceType.PAWN)
        assert not s.is_legal(p(6, 0), p(4, 0), blocker)

    def test_pawn_requires_clear_path(self):
        s = PawnStrategy(Color.WHITE)
        assert s.requires_clear_path()


class TestKingRequiresClearPath:
    def test_king_does_not_require_clear_path(self):
        assert not KingStrategy().requires_clear_path()

    def test_bishop_requires_clear_path(self):
        assert BishopStrategy().requires_clear_path()

    def test_base_strategy_requires_clear_path_true(self):
        from kungfu_chess.rules.piece_rules import MoveStrategy

        class Concrete(MoveStrategy):
            def is_legal(self, start, end, target):
                return True
        assert Concrete().requires_clear_path()


class TestKnightJumpsOverPieces:
    def test_knight_does_not_require_clear_path(self):
        assert not KnightStrategy().requires_clear_path()

    def test_knight_legal_even_with_pieces_in_between(self):
        s = KnightStrategy()
        blocker = make_piece(Color.WHITE, PieceType.PAWN)
        assert s.is_legal(p(0, 0), p(2, 1), blocker)
        assert s.is_legal(p(0, 0), p(2, 1), None)
