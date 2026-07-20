import pytest
import time
from kungfu_chess.realtime.game_engine import GameEngine as Game
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
        game.pending_cooldowns[0].ready_at = time.time() - 1
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
        game.pending_cooldowns[0].ready_at = time.time() - 1
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


class TestCooldown:
    def test_piece_is_cooling_after_arrival(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        from kungfu_chess.shared.constants import PieceState
        assert game.board.get_piece(0, 1).state == PieceState.COOLING
        assert len(game.pending_cooldowns) == 1

    def test_cooling_piece_cannot_move(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        result = game.request_move(p(0, 1), p(0, 2))
        assert not result.ok
        assert result.reason == "invalid_move"

    def test_piece_idle_after_cooldown_expires(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        game.pending_cooldowns[0].ready_at = time.time() - 1
        game.execute_pending_moves()
        from kungfu_chess.shared.constants import PieceState
        assert game.board.get_piece(0, 1).state == PieceState.IDLE
        assert len(game.pending_cooldowns) == 0

    def test_piece_can_move_after_cooldown(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        game.pending_cooldowns[0].ready_at = time.time() - 1
        game.execute_pending_moves()
        result = game.request_move(p(0, 1), p(0, 2))
        assert result.ok

    def test_snapshot_shows_is_cooling(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        snap = game.get_snapshot()
        assert snap.get(0, 1).is_cooling is True

    def test_snapshot_not_cooling_after_expiry(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        game.pending_cooldowns[0].ready_at = time.time() - 1
        game.execute_pending_moves()
        snap = game.get_snapshot()
        assert snap.get(0, 1).is_cooling is False

    def test_advance_time_expires_cooldown(self):
        from kungfu_chess.shared.constants import COOLDOWN_SECONDS
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        game.advance_time(int(COOLDOWN_SECONDS * 1000) + 100)
        game.execute_pending_moves()
        assert len(game.pending_cooldowns) == 0


class TestAdvanceTime:
    def test_advance_time_shifts_jump_land_at(self):
        game = Game(BOARD_JUMP)
        game.handle_jump(p(1, 1))
        land_at_before = game.pending_jumps[0].land_at
        game.advance_time(500)
        assert game.pending_jumps[0].land_at == pytest.approx(land_at_before, abs=0.01)


class TestResolveEdgeCases:
    def test_moving_piece_removed_from_board_is_cancelled(self):
        # piece disappears mid-flight (e.g. captured by jump) — move should be silently dropped
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 2))
        game.board.remove_piece(0, 0)  # simulate piece vanishing
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert len(game.pending_moves) == 0

    def test_friendly_piece_at_destination_cancels_move(self):
        # inject two moves manually to bypass schedule_move blocking logic
        # wB arrives at col=1 first; wR arrives second and finds a friendly there
        from kungfu_chess.realtime.motion import PendingMove
        board = [['wR', '.', 'wB']]
        game = Game(board)
        now = time.time()
        game.pending_moves.append(PendingMove(p(0, 2), p(0, 1), now - 2))  # wB first
        game.pending_moves.append(PendingMove(p(0, 0), p(0, 1), now - 1))  # wR second
        game.execute_pending_moves()
        assert game.board.get_piece(0, 0) is not None  # wR stayed
        assert game.board.get_piece(0, 1) is not None  # wB is there

    def test_non_king_capture_does_not_end_game(self):
        board = [['wR', 'bR']]
        game = Game(board)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert not game.is_game_over
        assert game.board.get_piece(0, 1) is not None

    def test_piece_blocked_at_first_square_stays_put(self):
        # wQ moves right col=1->col=2 (arrives col=2 after 1s)
        # wR moves right col=0->col=2 (arrives col=2 after 2s) — wQ blocks col=2, wR stops at col=1
        board = [['wR', 'wQ', '.']]
        game = Game(board)
        game.request_move(p(0, 1), p(0, 2))  # wQ -> col=2 after 1s
        game.request_move(p(0, 0), p(0, 2))  # wR -> col=2 after 2s, blocked by wQ
        rook_move = next(m for m in game.pending_moves if m.start == p(0, 0))
        assert rook_move.end == p(0, 1)

    def test_piece_blocked_immediately_stays_at_start(self):
        # wR at col=0 wants to move to col=1, but wQ is already heading to col=1 and arrives first
        # wR's first (and only) step is blocked — actual_end falls back to start
        board = [['wR', '.', 'wQ']]
        game = Game(board)
        game.request_move(p(0, 2), p(0, 1))  # wQ -> col=1 after 1s
        game.request_move(p(0, 0), p(0, 1))  # wR -> col=1 after 1s, same arrival — blocked
        rook_move = next(m for m in game.pending_moves if m.start == p(0, 0))
        assert rook_move.end == p(0, 0)


class TestFriendlyBlockingPath:
    def test_piece_stops_before_friendly_destination(self):
        # Queen at (4,3) moves right to (4,5) — arrives at (4,4) after 1s
        # Rook at (7,4) moves up to (0,4) — arrives at (4,4) after 3s
        # Queen arrives at (4,4) before Rook, so Rook should stop at (5,4)
        board = [
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', 'wQ', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', '.', '.', '.', '.'],
            ['.', '.', '.', '.', 'wR', '.', '.', '.'],
        ]
        game = Game(board)
        # Queen: (4,3)->(4,4), ends at (4,4) after 1 step
        game.request_move(p(4, 3), p(4, 4))
        # Rook: (7,4)->(0,4), reaches (4,4) after 3 steps
        game.request_move(p(7, 4), p(0, 4))
        rook_move = next(m for m in game.pending_moves if m.start == p(7, 4))
        # Rook should stop at (5,4), one step before (4,4)
        assert rook_move.end == p(5, 4)


class TestExpireHelpers:
    def test_expire_pending_moves(self):
        import time
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 2))
        game._expire_pending_moves()
        assert game.pending_moves[0].arrive_at < time.time()

    def test_expire_pending_cooldowns(self):
        import time
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        game._expire_pending_cooldowns()
        assert game.pending_cooldowns[0].ready_at < time.time()

    def test_expire_pending_jumps(self):
        import time
        game = Game(BOARD_JUMP)
        game.handle_jump(p(1, 1))
        game._expire_pending_jumps()
        assert game.pending_jumps[0].land_at < time.time()


class TestIsPendingEmpty:
    def test_is_pending_returns_false_when_no_moves(self):
        game = Game(BOARD_ROOKS)
        assert not game._arbiter.is_pending(p(0, 0))

    def test_returns_legal_destinations(self):
        game = Game(BOARD_ROOKS)
        moves = game.get_legal_moves(p(0, 0))
        assert p(0, 1) in moves
        assert p(0, 2) in moves
        assert p(1, 0) in moves

    def test_returns_empty_for_empty_cell(self):
        game = Game(BOARD_ROOKS)
        assert game.get_legal_moves(p(0, 1)) == []

    def test_excludes_friendly_fire(self):
        board = [['wR', 'wK']]
        game = Game(board)
        moves = game.get_legal_moves(p(0, 0))
        assert p(0, 1) not in moves


class TestHasPiece:
    def test_returns_true_for_idle_piece(self):
        game = Game(BOARD_ROOKS)
        assert game.has_piece(p(0, 0))

    def test_returns_false_for_empty_cell(self):
        game = Game(BOARD_ROOKS)
        assert not game.has_piece(p(0, 1))

    def test_returns_false_for_pending_piece(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 2))
        assert not game.has_piece(p(0, 0))

    def test_returns_false_for_cooling_piece(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert not game.has_piece(p(0, 1))

    def test_returns_false_out_of_bounds(self):
        game = Game(BOARD_ROOKS)
        assert not game.has_piece(p(99, 99))


class TestGameSnapshot:
    def test_get_game_snapshot_has_player_names(self):
        from kungfu_chess.model.player import Player
        from kungfu_chess.shared.constants import Color
        black = Player("Alice", Color.BLACK)
        white = Player("Bob", Color.WHITE)
        game = Game(BOARD_ROOKS, black, white)
        snap = game.get_game_snapshot()
        assert snap.black.name == "Alice"
        assert snap.white.name == "Bob"

    def test_get_game_snapshot_score_starts_zero(self):
        game = Game(BOARD_ROOKS)
        snap = game.get_game_snapshot()
        assert snap.black.score == 0
        assert snap.white.score == 0

    def test_get_game_snapshot_records_capture(self):
        game = Game(BOARD_ROOKS)
        game.request_move(p(0, 0), p(2, 0))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        snap = game.get_game_snapshot()
        assert snap.white.score == 5  # wR captured bR


class TestScoreTracker:
    def test_record_move_adds_entry(self):
        from kungfu_chess.realtime.score_tracker import ScoreTracker
        from kungfu_chess.model.player import Player
        from kungfu_chess.shared.constants import Color, PieceType
        tracker = ScoreTracker(Player("X", Color.WHITE))
        tracker.record_move(PieceType.ROOK, p(0, 0), p(0, 2), elapsed_secs=5.0)
        assert len(tracker.moves) == 1
        assert 'R' in tracker.moves[0][1]

    def test_record_capture_updates_score(self):
        from kungfu_chess.realtime.score_tracker import ScoreTracker
        from kungfu_chess.model.player import Player
        from kungfu_chess.shared.constants import Color, PieceType
        tracker = ScoreTracker(Player("X", Color.WHITE))
        tracker.record_capture(PieceType.QUEEN)
        assert tracker.score == 9
        assert PieceType.QUEEN in tracker.captured

    def test_captured_returns_copy(self):
        from kungfu_chess.realtime.score_tracker import ScoreTracker
        from kungfu_chess.model.player import Player
        from kungfu_chess.shared.constants import Color, PieceType
        tracker = ScoreTracker(Player("X", Color.WHITE))
        tracker.record_capture(PieceType.PAWN)
        captured = tracker.captured
        captured.clear()
        assert len(tracker.captured) == 1


class TestInvalidBoardError:
    def test_stores_errors(self):
        from kungfu_chess.shared.exceptions import InvalidBoardError
        err = InvalidBoardError(["e1", "e2"])
        assert err.errors == ["e1", "e2"]

    def test_message_contains_errors(self):
        from kungfu_chess.shared.exceptions import InvalidBoardError
        err = InvalidBoardError(["bad_token"])
        assert "bad_token" in str(err)


class TestKnightScheduleMove:
    def test_knight_schedules_single_step(self):
        board = [['wN', '.', '.'],
                 ['.', '.', '.'],
                 ['.', 'bR', '.']]
        game = Game(board)
        game.request_move(p(0, 0), p(2, 1))
        assert len(game.pending_moves) == 1
        assert game.pending_moves[0].end == p(2, 1)

    def test_get_snapshot_reflects_board(self):
        from kungfu_chess.shared.dto import PieceSnapshot
        from kungfu_chess.shared.constants import PieceType, Color
        game = make_game()
        snap = game.get_snapshot()
        assert snap.get(7, 1) == PieceSnapshot(Color.WHITE, PieceType.KING)

    def test_get_snapshot_after_move(self):
        from kungfu_chess.shared.constants import PieceType, Color, PieceState
        game = make_game()
        game.request_move(p(6, 1), p(5, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        snap = game.get_snapshot()
        piece = snap.get(5, 1)
        assert piece is not None
        assert piece.color == Color.WHITE
        assert piece.ptype == PieceType.PAWN
        assert piece.is_cooling is True
        assert piece.state == PieceState.COOLING
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
