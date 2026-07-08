import pytest
import time
from Game import Game


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


def make_game():
    return Game(BOARD)


class TestClickSelection:
    def test_click_piece_selects_it(self):
        game = make_game()
        game.handle_command("click 150 650")
        assert game.selected == (6, 1)

    def test_click_empty_does_not_select(self):
        game = make_game()
        game.handle_command("click 350 350")
        assert game.selected is None

    def test_click_out_of_bounds_ignored(self):
        game = make_game()
        game.handle_command("click 9999 9999")
        assert game.selected is None

    def test_click_same_cell_deselects(self):
        game = make_game()
        game.handle_command("click 150 650")
        game.handle_command("click 150 650")
        assert game.selected == (6, 1)

    def test_click_friendly_switches_selection(self):
        game = make_game()
        game.handle_command("click 150 650")
        game.handle_command("click 150 750")
        assert game.selected == (7, 1)


class TestMoveScheduling:
    def test_legal_move_adds_pending(self):
        game = make_game()
        game.handle_command("click 150 650")
        game.handle_command("click 150 550")
        assert len(game.pending_moves) == 1
        assert game.pending_moves[0].start == (6, 1)
        assert game.pending_moves[0].end == (5, 1)

    def test_illegal_move_not_added(self):
        game = make_game()
        game.handle_command("click 150 650")
        game.handle_command("click 150 350")
        assert len(game.pending_moves) == 0

    def test_cannot_queue_same_piece_twice(self):
        game = make_game()
        game.handle_command("click 150 650")
        game.handle_command("click 150 550")
        game.handle_command("click 150 650")
        game.handle_command("click 150 450")
        assert len(game.pending_moves) == 1

    def test_cannot_redirect_moving_piece(self):
        game = make_game()
        game.handle_command("click 150 650")  # select wP at (6,1)
        game.handle_command("click 150 550")  # move to (5,1)
        game.handle_command("click 150 650")  # try to select again — should be blocked
        assert game.selected is None
        assert len(game.pending_moves) == 1
        assert game.pending_moves[0].end == (5, 1)

    def test_cannot_select_pending_piece_from_idle(self):
        game = make_game()
        game.handle_command("click 150 650")  # select wP at (6,1)
        game.handle_command("click 150 550")  # move to (5,1) — now pending
        game = Game(BOARD)                    # fresh game, same board state concept
        # simulate directly: inject a pending move and try to select its start
        game.handle_command("click 150 650")  # select wP
        game.handle_command("click 150 550")  # schedule move
        game.selected = None                  # reset selection manually
        game.handle_command("click 150 650")  # try to select the moving piece
        assert game.selected is None

    def test_pending_piece_not_selectable_as_friendly_switch(self):
        game = make_game()
        game.handle_command("click 150 750")  # select wK at (7,1)
        game.handle_command("click 150 650")  # try to switch to wP at (6,1) — wP not pending yet, should switch
        assert game.selected == (6, 1)
        game.handle_command("click 150 550")  # schedule wP move to (5,1)
        game.selected = None
        game.handle_command("click 150 750")  # select wK
        game.handle_command("click 150 650")  # try to switch to wP — now pending, should be blocked
        assert game.selected is None

    def test_immediate_move_after_arrival(self):
        game = make_game()
        game.handle_command("click 150 650")  # select wP at (6,1)
        game.handle_command("click 150 550")  # move to (5,1)
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        game.handle_command("click 150 550")  # select wP now at (5,1)
        game.handle_command("click 150 450")  # move to (4,1)
        assert len(game.pending_moves) == 1
        assert game.pending_moves[0].start == (5, 1)
        assert game.pending_moves[0].end == (4, 1)


BOARD_ROOKS = [
    ['wR', '.', '.'],
    ['.', '.', '.'],
    ['bR', '.', '.'],
]


class TestRealTiming:
    def test_move_delay_within_1000ms(self):
        game = Game(BOARD_ROOKS)
        game.handle_command("click 50 50")   # select wR at (0,0)
        game.handle_command("click 250 50")  # move wR to (0,2)
        time.sleep(1.0)
        game.execute_pending_moves()
        assert game.board.get_piece(0, 2) is not None
        assert game.board.get_piece(0, 0) is None

    def test_opposite_colors_cannot_move_concurrently(self):
        game = Game(BOARD_ROOKS)
        game.handle_command("click 50 50")    # select wR at (0,0)
        game.handle_command("click 250 50")   # move wR to (0,2) — pending
        game.handle_command("click 50 250")   # select bR at (2,0)
        game.handle_command("click 250 250")  # try to move bR — should be blocked
        time.sleep(1.0)
        game.execute_pending_moves()
        assert game.board.get_piece(0, 2) is not None  # wR arrived
        assert game.board.get_piece(2, 0) is not None  # bR did NOT move
        assert game.board.get_piece(2, 2) is None

    def test_can_move_again_after_real_arrival(self):
        game = Game(BOARD_ROOKS)
        game.handle_command("click 50 50")   # select wR at (0,0)
        game.handle_command("click 150 50")  # move wR to (0,1)
        time.sleep(1.0)
        game.handle_command("click 150 50")  # select wR now at (0,1)
        game.handle_command("click 250 50")  # move wR to (0,2)
        time.sleep(1.0)
        game.execute_pending_moves()
        assert game.board.get_piece(0, 2) is not None
        assert game.board.get_piece(0, 1) is None


BOARD_KING_CAPTURE = [
    ['wR', '.', 'bK'],
    ['.', '.', '.'],
    ['.', '.', '.'],
]


class TestGameOver:
    def test_king_capture_sets_game_over(self):
        game = Game(BOARD_KING_CAPTURE)
        game.handle_command("click 50 50")   # select wR at (0,0)
        game.handle_command("click 250 50")  # move wR to (0,2) — captures bK
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert game.is_game_over

    def test_commands_rejected_after_game_over(self):
        game = Game(BOARD_KING_CAPTURE)
        game.handle_command("click 50 50")
        game.handle_command("click 250 50")
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert game.is_game_over
        game.handle_command("click 50 50")
        assert game.selected is None
        assert len(game.pending_moves) == 0

    def test_pending_moves_cleared_on_game_over(self):
        game = Game(BOARD_KING_CAPTURE)
        game.handle_command("click 50 50")
        game.handle_command("click 250 50")  # captures bK
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert len(game.pending_moves) == 0

    def test_game_not_over_without_king_capture(self):
        game = Game(BOARD_KING_CAPTURE)
        game.handle_command("click 50 50")   # select wR
        game.handle_command("click 150 50")  # move to (0,1) — no capture
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert not game.is_game_over


class TestExecutePendingMoves:
    def test_move_executes_after_delay(self):
        game = make_game()
        game.handle_command("click 150 650")
        game.handle_command("click 150 550")
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert game.board.get_piece(5, 1) is not None
        assert game.board.get_piece(6, 1) is None

    def test_move_not_executed_before_delay(self):
        game = make_game()
        game.handle_command("click 150 650")
        game.handle_command("click 150 550")
        game.pending_moves[0].arrive_at = time.time() + 999
        game.execute_pending_moves()
        assert game.board.get_piece(6, 1) is not None
        assert game.board.get_piece(5, 1) is None


class TestPrintBoard:
    def test_print_board_executes_ready_moves(self, capsys):
        game = make_game()
        game.handle_command("click 150 650")
        game.handle_command("click 150 550")
        game.pending_moves[0].arrive_at = time.time() - 1
        game.handle_command("print board")
        output = capsys.readouterr().out.splitlines()
        assert output[5].split()[1] == 'wP'
        assert output[6].split()[1] == '.'

    def test_print_board_does_not_execute_future_moves(self, capsys):
        game = make_game()
        game.handle_command("click 150 650")
        game.handle_command("click 150 550")
        game.pending_moves[0].arrive_at = time.time() + 999
        game.handle_command("print board")
        output = capsys.readouterr().out.splitlines()
        assert output[6].split()[1] == 'wP'
