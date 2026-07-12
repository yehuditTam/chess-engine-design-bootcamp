import pytest
import time
from kungfu_chess.engine.game_engine import GameEngine as Game
from kungfu_chess.model.position import Position


def p(r, c):
    return Position(r, c)


BOARD = [
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', 'wP', '.', '.', '.', '.', '.', '.'],
    ['.', 'wK', '.', '.', '.', '.', '.', 'bK'],
]

BOARD_ROOKS = [
    ['wR', '.', '.'],
    ['.', '.', '.'],
    ['bR', '.', '.'],
]

BOARD_KING_CAPTURE = [
    ['wR', '.', 'bK'],
    ['.', '.', '.'],
    ['.', '.', '.'],
]

BOARD_PAWN_DOUBLE = [
    ['.', '.', '.'],
    ['.', '.', '.'],
    ['.', '.', '.'],
    ['.', '.', '.'],
    ['.', '.', '.'],
    ['.', '.', '.'],
    ['wP', '.', '.'],
    ['.', '.', '.'],
]

BOARD_PAWN_PROMOTION = [
    ['.', '.', '.'],
    ['wP', '.', '.'],
    ['.', '.', '.'],
]

BOARD_JUMP = [
    ['.', 'bR', '.'],
    ['.', 'wR', '.'],
    ['.', '.', '.'],
]


def make_game():
    return Game(BOARD)


class TestRequestMove:
    def test_legal_move_schedules_pending(self):
        game = Game(BOARD_ROOKS)
        result = game.request_move(p(0, 0), p(0, 1))
        assert result.ok
        assert len(game.pending_moves) == 1
        assert game.pending_moves[0].start == p(0, 0)
        assert game.pending_moves[0].end == p(0, 1)

    def test_illegal_move_not_scheduled(self):
        game = Game(BOARD_ROOKS)
        result = game.request_move(p(0, 0), p(1, 1))  # diagonal — illegal for rook
        assert not result.ok
        assert result.reason == "invalid_move"
        assert len(game.pending_moves) == 0

    def test_friendly_fire_rejected(self):
        board = [['wR', 'wK']]
        game = Game(board)
        result = game.request_move(p(0, 0), p(0, 1))
        assert not result.ok
        assert len(game.pending_moves) == 0

    def test_pending_piece_cannot_move_again(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        result = game.request_move(p(0, 0), p(0, 2))
        assert not result.ok
        assert len(game.pending_moves) == 1

    def test_game_over_rejects_move(self):
        game = Game(BOARD_KING_CAPTURE)
        game.request_move(p(0, 0), p(0, 2))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        result = game.request_move(p(0, 2), p(1, 2))
        assert not result.ok
        assert result.reason == "game_over"

    def test_motion_in_progress_rejects_other_color(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 2))  # wR moving
        result = game.request_move(p(2, 0), p(2, 2))  # bR — blocked
        assert not result.ok
        assert result.reason == "motion_in_progress"


class TestMoveScaling:
    def test_one_square_move_duration(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        assert game.pending_moves[0].arrive_at == pytest.approx(time.time() + 1.0, abs=0.1)

    def test_two_square_move_duration(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 2))
        assert game.pending_moves[0].arrive_at == pytest.approx(time.time() + 2.0, abs=0.1)


class TestExecutePendingMoves:
    def test_move_executes_after_delay(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert game.board.get_piece(0, 1) is not None
        assert game.board.get_piece(0, 0) is None

    def test_move_not_executed_before_delay(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() + 999
        game.execute_pending_moves()
        assert game.board.get_piece(0, 0) is not None
        assert game.board.get_piece(0, 1) is None

    def test_can_move_again_after_arrival(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        game.request_move(p(0, 1), p(0, 2))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert game.board.get_piece(0, 2) is not None
        assert game.board.get_piece(0, 1) is None


class TestGameOver:
    def test_king_capture_sets_game_over(self):
        game = Game(BOARD_KING_CAPTURE)
        game.request_move(p(0, 0), p(0, 2))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert game.is_game_over

    def test_pending_moves_cleared_on_game_over(self):
        game = Game(BOARD_KING_CAPTURE)
        game.request_move(p(0, 0), p(0, 2))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert len(game.pending_moves) == 0

    def test_game_not_over_without_king_capture(self):
        game = Game(BOARD_KING_CAPTURE)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert not game.is_game_over


class TestPawnRules:
    def test_pawn_single_move(self):
        game = Game(BOARD_PAWN_DOUBLE)
        result = game.request_move(p(6, 0), p(5, 0))
        assert result.ok
        assert game.pending_moves[0].end == p(5, 0)

    def test_pawn_double_move_from_start(self):
        game = Game(BOARD_PAWN_DOUBLE)
        result = game.request_move(p(6, 0), p(4, 0))
        assert result.ok
        assert game.pending_moves[0].end == p(4, 0)

    def test_pawn_double_move_blocked(self):
        board = [
            ['.', '.', '.'],
            ['.', '.', '.'],
            ['.', '.', '.'],
            ['.', '.', '.'],
            ['.', '.', '.'],
            ['bR', '.', '.'],
            ['wP', '.', '.'],
            ['.', '.', '.'],
        ]
        game = Game(board)
        result = game.request_move(p(6, 0), p(4, 0))
        assert not result.ok
        assert len(game.pending_moves) == 0

    def test_pawn_double_move_not_allowed_after_start(self):
        game = Game(BOARD_PAWN_DOUBLE)
        game.request_move(p(6, 0), p(5, 0))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        result = game.request_move(p(5, 0), p(3, 0))
        assert not result.ok
        assert len(game.pending_moves) == 0

    def test_pawn_promotion_to_queen(self):
        game = Game(BOARD_PAWN_PROMOTION)
        game.request_move(p(1, 0), p(0, 0))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        from kungfu_chess.shared.constants import PieceType
        assert game.board.get_piece(0, 0).ptype == PieceType.QUEEN

    def test_promoted_queen_can_move_diagonally(self):
        game = Game(BOARD_PAWN_PROMOTION)
        game.request_move(p(1, 0), p(0, 0))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        result = game.request_move(p(0, 0), p(1, 1))
        assert result.ok


class TestJump:
    def test_jump_schedules_pending_jump(self):
        game = Game(BOARD_JUMP)
        game.handle_jump(p(1, 1))
        assert len(game.pending_jumps) == 1
        assert game.pending_jumps[0].cell == p(1, 1)

    def test_airborne_piece_stays_on_cell(self):
        game = Game(BOARD_JUMP)
        game.handle_jump(p(1, 1))
        assert game.board.get_piece(1, 1) is not None

    def test_airborne_captures_arriving_enemy(self):
        game = Game(BOARD_JUMP)
        game.handle_jump(p(1, 1))
        game.request_move(p(0, 1), p(1, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert game.board.get_piece(1, 1) is not None
        assert game.board.get_piece(1, 1).color.value == 'w'
        assert game.board.get_piece(0, 1) is None

    def test_no_enemy_arrives_piece_lands_normally(self):
        game = Game(BOARD_JUMP)
        game.handle_jump(p(1, 1))
        game.pending_jumps[0].land_at = time.time() - 1
        game.execute_pending_moves()
        assert len(game.pending_jumps) == 0
        assert game.board.get_piece(1, 1) is not None

    def test_moving_piece_cannot_jump(self):
        game = Game(BOARD_JUMP)
        game.request_move(p(1, 1), p(2, 1))
        game.handle_jump(p(1, 1))
        assert len(game.pending_jumps) == 0

    def test_cannot_jump_twice(self):
        game = Game(BOARD_JUMP)
        game.handle_jump(p(1, 1))
        game.handle_jump(p(1, 1))
        assert len(game.pending_jumps) == 1

    def test_friendly_arriving_piece_not_captured_by_airborne(self):
        board = [
            ['.', 'wB', '.'],
            ['.', 'wR', '.'],
            ['.', '.', '.'],
        ]
        game = Game(board)
        game.handle_jump(p(1, 1))
        result = game.request_move(p(0, 1), p(1, 1))
        assert not result.ok
        assert len(game.pending_moves) == 0

    def test_black_piece_can_jump(self):
        board = [
            ['.', '.', '.'],
            ['.', 'bR', '.'],
            ['.', 'wR', '.'],
        ]
        game = Game(board)
        game.handle_jump(p(1, 1))
        assert len(game.pending_jumps) == 1
        assert game.pending_jumps[0].cell == p(1, 1)


class TestGetSnapshot:
    def test_get_snapshot_reflects_board(self):
        from kungfu_chess.shared.dto import PieceSnapshot
        from kungfu_chess.shared.constants import PieceType, Color
        game = make_game()
        snap = game.get_snapshot()
        assert snap.get(7, 1) == PieceSnapshot(Color.WHITE, PieceType.KING)

    def test_get_snapshot_after_move(self):
        from kungfu_chess.shared.dto import PieceSnapshot
        from kungfu_chess.shared.constants import PieceType, Color
        game = make_game()
        game.request_move(p(6, 1), p(5, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        snap = game.get_snapshot()
        assert snap.get(5, 1) == PieceSnapshot(Color.WHITE, PieceType.PAWN)
        assert snap.get(6, 1) is None


class TestPrintBoard:
    def test_print_board_executes_ready_moves(self, capsys):
        from kungfu_chess.input.commands import PrintBoardCommand
        from kungfu_chess.input.controller import Controller
        game = make_game()
        controller = Controller(game, board_cols=8, board_rows=8)
        game.request_move(p(6, 1), p(5, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        controller.handle_command(PrintBoardCommand())
        output = capsys.readouterr().out.splitlines()
        assert output[5].split()[1] == 'wP'
        assert output[6].split()[1] == '.'

    def test_print_board_does_not_execute_future_moves(self, capsys):
        from kungfu_chess.input.commands import PrintBoardCommand
        from kungfu_chess.input.controller import Controller
        game = make_game()
        controller = Controller(game, board_cols=8, board_rows=8)
        game.request_move(p(6, 1), p(5, 1))
        game.pending_moves[0].arrive_at = time.time() + 999
        controller.handle_command(PrintBoardCommand())
        output = capsys.readouterr().out.splitlines()
        assert output[6].split()[1] == 'wP'
