import time
import pytest
from kungfu_chess.engine.game_engine import GameEngine
from kungfu_chess.input.controller import Controller
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


def make_controller(board=None):
    rows = board or BOARD
    game = GameEngine(rows)
    return Controller(game, board_cols=len(rows[0]), board_rows=len(rows)), game


class TestSelection:
    def test_click_piece_selects_it(self):
        ctrl, _ = make_controller()
        ctrl.handle_click(p(6, 1))
        assert ctrl.selected == p(6, 1)

    def test_click_empty_does_not_select(self):
        ctrl, _ = make_controller()
        ctrl.handle_click(p(3, 3))
        assert ctrl.selected is None

    def test_click_out_of_bounds_ignored_when_no_selection(self):
        ctrl, _ = make_controller()
        ctrl.handle_click(p(99, 99))
        assert ctrl.selected is None

    def test_click_out_of_bounds_cancels_selection(self):
        ctrl, _ = make_controller()
        ctrl.handle_click(p(6, 1))
        ctrl.handle_click(p(99, 99))
        assert ctrl.selected is None

    def test_second_click_on_friendly_switches_selection(self):
        ctrl, _ = make_controller()
        ctrl.handle_click(p(6, 1))   # select wP
        ctrl.handle_click(p(7, 1))   # switch to wK
        assert ctrl.selected == p(7, 1)

    def test_second_click_on_pending_friendly_clears_selection(self):
        ctrl, game = make_controller(BOARD_ROOKS)
        ctrl.handle_click(p(0, 0))   # select wR
        ctrl.handle_click(p(0, 2))   # schedule move — wR now pending
        ctrl.handle_click(p(0, 0))   # try to select pending wR as friendly switch
        assert ctrl.selected is None

    def test_selection_cleared_after_move(self):
        ctrl, _ = make_controller()
        ctrl.handle_click(p(6, 1))
        ctrl.handle_click(p(5, 1))
        assert ctrl.selected is None

    def test_selection_cleared_after_illegal_move(self):
        ctrl, _ = make_controller()
        ctrl.handle_click(p(6, 1))
        ctrl.handle_click(p(3, 1))   # illegal — 3 squares
        assert ctrl.selected is None


class TestMoveScheduling:
    def test_legal_move_schedules_pending(self):
        ctrl, game = make_controller(BOARD_ROOKS)
        ctrl.handle_click(p(0, 0))
        ctrl.handle_click(p(0, 1))
        assert len(game.pending_moves) == 1
        assert game.pending_moves[0].start == p(0, 0)
        assert game.pending_moves[0].end == p(0, 1)

    def test_cannot_move_pending_piece(self):
        ctrl, game = make_controller(BOARD_ROOKS)
        ctrl.handle_click(p(0, 0))
        ctrl.handle_click(p(0, 1))   # wR now pending
        ctrl.handle_click(p(0, 0))   # try to select pending wR — has_piece returns False
        assert ctrl.selected is None
        assert len(game.pending_moves) == 1

    def test_opposite_color_blocked_while_motion_active(self):
        ctrl, game = make_controller(BOARD_ROOKS)
        ctrl.handle_click(p(0, 0))
        ctrl.handle_click(p(0, 2))   # wR moving
        ctrl.handle_click(p(2, 0))   # select bR
        ctrl.handle_click(p(2, 2))   # try to move bR — motion_in_progress
        assert len(game.pending_moves) == 1   # only wR pending

    def test_move_after_arrival(self):
        ctrl, game = make_controller(BOARD_ROOKS)
        ctrl.handle_click(p(0, 0))
        ctrl.handle_click(p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        ctrl.handle_click(p(0, 1))
        ctrl.handle_click(p(0, 2))
        assert len(game.pending_moves) == 1
        assert game.pending_moves[0].start == p(0, 1)
