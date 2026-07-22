"""
Tests targeting the two uncovered lines in RealTimeArbiter and MoveStrategy.

real_time_arbiter.py line 65:
    The `break` inside _other_occupies_at when ocurr reaches other.end without
    having matched the target cell — i.e. the other piece's path ends before
    reaching `cell`.

piece_rules.py line 12:
    MoveStrategy.requires_clear_path() base implementation (returns True).
    Already covered by TestKingRequiresClearPath in test_move_rules.py via a
    concrete subclass, but the base body itself is only hit when called through
    a non-overriding subclass — the Concrete helper there does NOT override it,
    so it IS covered.  The real gap is that coverage marks the `return True`
    line as missed when only abstract subclasses that override it are exercised.
    We add an explicit call through a non-overriding concrete subclass here.
"""

import time
import pytest
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.realtime.motion import PendingMove
from kungfu_chess.model.board import Board
from kungfu_chess.model.position import Position
from kungfu_chess.rules.piece_rules import MoveStrategy, RookStrategy
from kungfu_chess.shared.constants import PieceState


def p(r, c):
    return Position(r, c)


# ---------------------------------------------------------------------------
# MoveStrategy base — requires_clear_path() line 12
# ---------------------------------------------------------------------------

class TestMoveStrategyBase:
    def test_base_requires_clear_path_returns_true(self):
        class Minimal(MoveStrategy):
            def is_legal(self, start, end, target):
                return True
        assert Minimal().requires_clear_path() is True


# ---------------------------------------------------------------------------
# RealTimeArbiter._other_occupies_at — the `break` on line 65
# ---------------------------------------------------------------------------

class TestOtherOccupiesAt:
    def test_other_path_ends_before_cell_returns_false(self):
        board = Board([['wR', '.', '.', 'wQ']])
        arbiter = RealTimeArbiter(board)
        arbiter.schedule_move(p(0, 3), p(0, 1))   # wQ: (0,3)->(0,1)
        arbiter.schedule_move(p(0, 0), p(0, 2))   # wR: (0,0)->(0,2)
        rook_move = next(m for m in arbiter.pending_moves if m.start == p(0, 0))
        assert rook_move.end == p(0, 2)

    def test_other_occupies_at_returns_true_when_path_overlaps(self):
        board = Board([['wR', '.', 'wQ']])
        arbiter = RealTimeArbiter(board)
        arbiter.schedule_move(p(0, 2), p(0, 1))   # wQ: 1 step
        arbiter.schedule_move(p(0, 0), p(0, 1))   # wR: 1 step — blocked
        rook_move = next(m for m in arbiter.pending_moves if m.start == p(0, 0))
        assert rook_move.end == p(0, 0)


# ---------------------------------------------------------------------------
# _moving_piece_captured_by_airborne — moving piece is None (line 112)
# ---------------------------------------------------------------------------

class TestMovingPieceNone:
    def test_moving_piece_already_gone_is_skipped(self):
        """If the piece at move.start is None, the move is removed silently."""
        board = Board([['wR', '.', 'bK']])
        arbiter = RealTimeArbiter(board)
        arbiter.schedule_move(p(0, 0), p(0, 2))
        move = arbiter.pending_moves[0]
        move.arrive_at = arbiter._now() - 1
        # Remove the piece manually to simulate it already being gone
        board.remove_piece(0, 0)
        completed, jump_captures, target = arbiter.execute_pending_moves()
        assert completed == []
        assert target is None
        assert move not in arbiter.pending_moves


# ---------------------------------------------------------------------------
# moving_color() — all pending pieces are None on the board (line 92)
# ---------------------------------------------------------------------------

class TestMovingColorNone:
    def test_moving_color_returns_none_when_piece_gone(self):
        board = Board([['wR', '.']])
        arbiter = RealTimeArbiter(board)
        arbiter.schedule_move(p(0, 0), p(0, 1))
        board.remove_piece(0, 0)  # piece vanishes mid-flight
        assert arbiter.moving_color() is None


# ---------------------------------------------------------------------------
# _compute_actual_end — path reaches end without any block (line 124)
# ---------------------------------------------------------------------------

class TestComputeActualEndNoBlock:
    def test_unblocked_path_returns_original_end(self):
        board = Board([['wR', '.', '.']])
        arbiter = RealTimeArbiter(board)
        arbiter.schedule_move(p(0, 0), p(0, 2))
        move = arbiter.pending_moves[0]
        assert move.end == p(0, 2)


# ---------------------------------------------------------------------------
# _is_blocked_by_friendly — other_piece is None (line 131)
# ---------------------------------------------------------------------------

class TestIsBlockedOtherPieceNone:
    def test_none_piece_in_pending_does_not_block(self):
        """A stale PendingMove whose piece is gone should not block other pieces."""
        board = Board([['wR', '.', 'wQ']])
        arbiter = RealTimeArbiter(board)
        # Manually inject a stale move whose piece no longer exists on the board
        stale = PendingMove(p(0, 2), p(0, 1), arbiter._now() + 10)
        arbiter.pending_moves.append(stale)
        board.remove_piece(0, 2)  # piece is gone
        # Now schedule wR — the stale move should be skipped (other_piece is None)
        arbiter.schedule_move(p(0, 0), p(0, 1))
        rook_move = next(m for m in arbiter.pending_moves if m.start == p(0, 0))
        assert rook_move.end == p(0, 1)  # not blocked by the None piece


# ---------------------------------------------------------------------------
# _will_occupy_before — other.end != cell (line 153)
# ---------------------------------------------------------------------------

class TestWillOccupyBeforeEndNotCell:
    def test_other_end_differs_from_cell_returns_false(self):
        board = Board([['wR', '.', 'wQ', '.']])
        arbiter = RealTimeArbiter(board)
        # wQ moves to col=3, wR moves to col=1 — wQ's end (col=3) != wR's target (col=1)
        arbiter.schedule_move(p(0, 2), p(0, 3))
        arbiter.schedule_move(p(0, 0), p(0, 1))
        rook_move = next(m for m in arbiter.pending_moves if m.start == p(0, 0))
        assert rook_move.end == p(0, 1)  # not blocked


# ---------------------------------------------------------------------------
# _check_jump_capture — destination not airborne (line 177)
# ---------------------------------------------------------------------------

class TestCheckJumpCaptureNotAirborne:
    def test_non_airborne_destination_returns_none(self):
        board = Board([['wR', 'bR', '.']])
        arbiter = RealTimeArbiter(board)
        arbiter.schedule_move(p(0, 0), p(0, 1))
        move = arbiter.pending_moves[0]
        move.arrive_at = arbiter._now() - 1
        # No jump scheduled — destination is not airborne
        result = arbiter._check_jump_capture(move)
        assert result is None

    def test_friendly_at_dest_cancels_move(self):
        """If a friendly piece is at the destination when the move resolves,
        the moving piece returns to IDLE and the move is discarded."""
        board = Board([['wR', 'wQ', '.']])
        arbiter = RealTimeArbiter(board)
        # Force a move from (0,0) to (0,1) where wQ already sits
        move = PendingMove(p(0, 0), p(0, 1), arbiter._now() - 1)
        arbiter.pending_moves.append(move)
        completed, _, target = arbiter.execute_pending_moves()
        assert completed == []
        assert target is None
        rook = board.get_piece(0, 0)
        assert rook is not None
        assert rook.state == PieceState.IDLE
