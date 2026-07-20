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


def p(r, c):
    return Position(r, c)


# ---------------------------------------------------------------------------
# MoveStrategy base — requires_clear_path() line 12
# ---------------------------------------------------------------------------

class TestMoveStrategyBase:
    def test_base_requires_clear_path_returns_true(self):
        """Directly exercise the base-class body of requires_clear_path."""
        class Minimal(MoveStrategy):
            def is_legal(self, start, end, target):
                return True
        # does NOT override requires_clear_path → hits line 12
        assert Minimal().requires_clear_path() is True


# ---------------------------------------------------------------------------
# RealTimeArbiter._other_occupies_at — the `break` on line 65
# ---------------------------------------------------------------------------

class TestOtherOccupiesAt:
    """
    _other_occupies_at returns False when the other piece's path ends before
    reaching `cell`.  This exercises the `break` branch (line 65).

    Setup:
      - wR at (0,0) wants to move right to (0,2).
      - wQ at (0,3) also moves left to (0,1).
      - When computing wR's actual end, _compute_actual_end checks whether wQ
        will occupy (0,1) before wR arrives there.
      - wQ's path is (0,3)->(0,2)->(0,1); it reaches (0,1) in 2 steps.
      - wR reaches (0,1) in 1 step — wQ arrives later, so no block at (0,1).
      - wR then checks (0,2): wQ's path ends at (0,1), so the inner loop hits
        `break` without returning True → _other_occupies_at returns False.
    """

    def _make_board(self, tokens):
        """Build a 1-row Board from a list of token strings."""
        return Board([tokens])

    def test_other_path_ends_before_cell_returns_false(self):
        board = self._make_board(['wR', '.', '.', 'wQ'])
        arbiter = RealTimeArbiter(board)
        # Schedule wQ first so it is in pending_moves when wR is scheduled
        arbiter.schedule_move(p(0, 3), p(0, 1))   # wQ: (0,3)->(0,1), 2 steps
        arbiter.schedule_move(p(0, 0), p(0, 2))   # wR: (0,0)->(0,2)
        # wR should reach (0,2) unobstructed because wQ stops at (0,1)
        rook_move = next(m for m in arbiter.pending_moves if m.start == p(0, 0))
        assert rook_move.end == p(0, 2)

    def test_other_occupies_at_returns_true_when_path_overlaps(self):
        """Sanity: when the other piece DOES reach the cell first, it blocks."""
        board = self._make_board(['wR', '.', 'wQ'])
        arbiter = RealTimeArbiter(board)
        arbiter.schedule_move(p(0, 2), p(0, 1))   # wQ: (0,2)->(0,1), 1 step
        arbiter.schedule_move(p(0, 0), p(0, 1))   # wR: (0,0)->(0,1), 1 step — same arrival
        rook_move = next(m for m in arbiter.pending_moves if m.start == p(0, 0))
        # wQ arrives at (0,1) at the same time — wR is blocked, stays at start
        assert rook_move.end == p(0, 0)
