"""Tests for client/auth.py and client/remote_game.py."""

import pytest
from unittest.mock import MagicMock
from kungfu_chess.model.position import Position
from kungfu_chess.shared.constants import Color, PieceState
from kungfu_chess.shared.dto import MoveResult
from client.remote_game import RemoteGame


# ---------------------------------------------------------------------------
# RemoteGame
# ---------------------------------------------------------------------------

def _make_snapshot(game_over=False, color=Color.WHITE, state=PieceState.IDLE):
    from kungfu_chess.shared.dto import (
        GameSnapshot, BoardSnapshot, PlayerSnapshot, PieceSnapshot
    )
    from kungfu_chess.shared.constants import PieceType
    piece = PieceSnapshot(color=color, ptype=PieceType.ROOK, state=state)
    grid = ((piece, None), (None, None))
    board = BoardSnapshot(grid=grid, rows=2, cols=2)
    black = PlayerSnapshot("B", Color.BLACK, 0, (), ())
    white = PlayerSnapshot("W", Color.WHITE, 0, (), ())
    return GameSnapshot(board=board, black=black, white=white, game_over=game_over)


class TestRemoteGame:
    def _bridge(self):
        return MagicMock()

    def test_snapshot_none_before_update(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        assert rg.snapshot is None

    def test_snapshot_set_after_update(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        snap = _make_snapshot()
        rg.update(snap)
        assert rg.snapshot is snap

    def test_is_game_over_false_before_update(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        assert rg.is_game_over is False

    def test_is_game_over_false_when_not_over(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        rg.update(_make_snapshot(game_over=False))
        assert rg.is_game_over is False

    def test_is_game_over_true_when_over(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        rg.update(_make_snapshot(game_over=True))
        assert rg.is_game_over is True

    def test_has_piece_false_before_update(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        assert rg.has_piece(Position(0, 0)) is False

    def test_has_piece_true_for_idle_own_piece(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        rg.update(_make_snapshot(color=Color.WHITE, state=PieceState.IDLE))
        assert rg.has_piece(Position(0, 0)) is True

    def test_has_piece_false_for_opponent_piece(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        rg.update(_make_snapshot(color=Color.BLACK, state=PieceState.IDLE))
        assert rg.has_piece(Position(0, 0)) is False

    def test_has_piece_false_for_moving_piece(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        rg.update(_make_snapshot(color=Color.WHITE, state=PieceState.MOVING))
        assert rg.has_piece(Position(0, 0)) is False

    def test_has_piece_false_for_cooling_piece(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        rg.update(_make_snapshot(color=Color.WHITE, state=PieceState.COOLING))
        assert rg.has_piece(Position(0, 0)) is False

    def test_has_piece_false_for_captured_piece(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        rg.update(_make_snapshot(color=Color.WHITE, state=PieceState.CAPTURED))
        assert rg.has_piece(Position(0, 0)) is False

    def test_has_piece_false_for_empty_cell(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        rg.update(_make_snapshot())
        assert rg.has_piece(Position(0, 1)) is False

    def test_request_move_sends_to_bridge(self):
        bridge = self._bridge()
        rg = RemoteGame(bridge, Color.WHITE)
        result = rg.request_move(Position(0, 0), Position(0, 1))
        bridge.send_move.assert_called_once_with(Position(0, 0), Position(0, 1))
        assert result == MoveResult(ok=True)

    def test_handle_jump_sends_to_bridge(self):
        bridge = self._bridge()
        rg = RemoteGame(bridge, Color.WHITE)
        rg.handle_jump(Position(1, 2))
        bridge.send_jump.assert_called_once_with(Position(1, 2))

    def test_get_legal_moves_requests_from_bridge_and_returns_empty(self):
        bridge = self._bridge()
        rg = RemoteGame(bridge, Color.WHITE)
        result = rg.get_legal_moves(Position(0, 0))
        bridge.request_legal_moves.assert_called_once_with(Position(0, 0))
        assert result == []

    def test_execute_pending_moves_is_noop(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        rg.execute_pending_moves()  # must not raise

    def test_advance_time_is_noop(self):
        rg = RemoteGame(self._bridge(), Color.WHITE)
        rg.advance_time(1000)  # must not raise


# ---------------------------------------------------------------------------
# auth.prompt_auth
# ---------------------------------------------------------------------------

class TestPromptAuth:
    def test_login_success_returns_username(self):
        from client.auth import prompt_auth
        bridge = MagicMock()
        bridge.authenticate.return_value = {
            "type": "auth_ok", "username": "alice", "rating": 1200
        }
        with pytest.MonkeyPatch().context() as mp:
            inputs = iter(["l", "alice"])
            mp.setattr("builtins.input", lambda _: next(inputs))
            mp.setattr("getpass.getpass", lambda _: "secret")
            result = prompt_auth(bridge)
        assert result == "alice"
        bridge.send_join.assert_called_once_with("alice")

    def test_register_success_returns_username(self):
        from client.auth import prompt_auth
        bridge = MagicMock()
        bridge.authenticate.return_value = {
            "type": "auth_ok", "username": "bob", "rating": 1200
        }
        with pytest.MonkeyPatch().context() as mp:
            inputs = iter(["r", "bob"])
            mp.setattr("builtins.input", lambda _: next(inputs))
            mp.setattr("getpass.getpass", lambda _: "pass")
            result = prompt_auth(bridge)
        assert result == "bob"
        bridge.authenticate.assert_called_once_with("bob", "pass", "register")

    def test_retries_on_auth_fail(self):
        from client.auth import prompt_auth
        bridge = MagicMock()
        bridge.authenticate.side_effect = [
            {"type": "auth_fail", "reason": "invalid credentials"},
            {"type": "auth_ok", "username": "carol", "rating": 1200},
        ]
        with pytest.MonkeyPatch().context() as mp:
            inputs = iter(["l", "carol", "l", "carol"])
            mp.setattr("builtins.input", lambda _: next(inputs))
            mp.setattr("getpass.getpass", lambda _: "pwd")
            result = prompt_auth(bridge)
        assert result == "carol"
        assert bridge.authenticate.call_count == 2
