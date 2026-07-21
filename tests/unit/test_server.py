"""
Tests for server/game_server.py.

Uses unittest.mock to replace websockets so no real network is needed.
db.authenticate / db.register are patched so tests need no real SQLite file.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch
from kungfu_chess.shared.constants import Color
from server.game_server import GameServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ws(messages=()):
    """Mock websocket that yields messages when iterated and records sends."""
    ws = AsyncMock()
    ws.sent = []

    async def _send(data):
        ws.sent.append(json.loads(data))

    ws.send = _send
    _iter = iter([json.dumps(m) for m in messages])

    async def _anext(self):
        try:
            return next(_iter)
        except StopIteration:
            raise StopAsyncIteration

    ws.__aiter__ = lambda self: self
    ws.__anext__ = _anext
    ws.close = AsyncMock()
    # Default recv: auth then join
    _recv_msgs = iter([
        json.dumps({"type": "auth", "action": "login", "username": "Alice", "password": "x"}),
        json.dumps({"type": "join", "username": "Alice"}),
    ])
    async def _recv():
        return next(_recv_msgs)
    ws.recv = _recv
    return ws


def run(coro):
    return asyncio.run(coro)


def patch_db_ok(username="Alice", rating=1200):
    """Patch db so authenticate returns True and get_rating returns rating."""
    return patch.multiple(
        "server.game_server.db",
        authenticate=lambda u, p: True,
        register=lambda u, p: True,
        get_rating=lambda u: rating,
        update_ratings=lambda w, l: (16, -16),
    )


# ---------------------------------------------------------------------------
# _assign_color
# ---------------------------------------------------------------------------

class TestAssignColor:
    def test_first_client_gets_white(self):
        server = GameServer()
        color = run(server._assign_color(make_ws()))
        assert color == Color.WHITE

    def test_second_client_gets_black(self):
        server = GameServer()
        run(server._assign_color(make_ws()))
        color = run(server._assign_color(make_ws()))
        assert color == Color.BLACK

    def test_third_client_gets_none(self):
        server = GameServer()
        run(server._assign_color(make_ws()))
        run(server._assign_color(make_ws()))
        assert run(server._assign_color(make_ws())) is None


# ---------------------------------------------------------------------------
# _on_connect — server full
# ---------------------------------------------------------------------------

class TestOnConnectServerFull:
    def test_server_full_sends_error_and_closes(self):
        server = GameServer()
        run(server._assign_color(make_ws()))
        run(server._assign_color(make_ws()))
        ws = make_ws()
        run(server._on_connect(ws))
        assert any(m.get("type") == "error" for m in ws.sent)
        ws.close.assert_called_once()


# ---------------------------------------------------------------------------
# _process_auth
# ---------------------------------------------------------------------------

class TestProcessAuth:
    def test_login_success(self):
        server = GameServer()
        with patch("server.game_server.db.authenticate", return_value=True), \
             patch("server.game_server.db.get_rating", return_value=1350):
            result = server._process_auth(
                {"type": "auth", "action": "login", "username": "alice", "password": "x"},
                Color.WHITE,
            )
        assert result["type"] == "auth_ok"
        assert result["username"] == "alice"
        assert result["rating"] == 1350

    def test_login_wrong_password(self):
        server = GameServer()
        with patch("server.game_server.db.authenticate", return_value=False):
            result = server._process_auth(
                {"type": "auth", "action": "login", "username": "alice", "password": "bad"},
                Color.WHITE,
            )
        assert result["type"] == "auth_fail"
        assert "credentials" in result["reason"]

    def test_register_success(self):
        server = GameServer()
        with patch("server.game_server.db.register", return_value=True), \
             patch("server.game_server.db.get_rating", return_value=1200):
            result = server._process_auth(
                {"type": "auth", "action": "register", "username": "newuser", "password": "p"},
                Color.WHITE,
            )
        assert result["type"] == "auth_ok"

    def test_register_duplicate_username(self):
        server = GameServer()
        with patch("server.game_server.db.register", return_value=False):
            result = server._process_auth(
                {"type": "auth", "action": "register", "username": "taken", "password": "p"},
                Color.WHITE,
            )
        assert result["type"] == "auth_fail"
        assert "taken" in result["reason"]

    def test_empty_username_fails(self):
        server = GameServer()
        result = server._process_auth(
            {"type": "auth", "action": "login", "username": "", "password": "x"},
            Color.WHITE,
        )
        assert result["type"] == "auth_fail"
        assert "username" in result["reason"]

    def test_stores_username_and_rating_on_success(self):
        server = GameServer()
        with patch("server.game_server.db.authenticate", return_value=True), \
             patch("server.game_server.db.get_rating", return_value=1400):
            server._process_auth(
                {"type": "auth", "action": "login", "username": "bob", "password": "x"},
                Color.BLACK,
            )
        assert server._usernames[Color.BLACK] == "bob"
        assert server._ratings[Color.BLACK] == 1400


# ---------------------------------------------------------------------------
# _auth_loop
# ---------------------------------------------------------------------------

class TestAuthLoop:
    def test_auth_loop_succeeds_on_first_try(self):
        server = GameServer()
        ws = make_ws()
        with patch_db_ok():
            result = run(server._auth_loop(ws, Color.WHITE))
        assert result is True
        assert any(m.get("type") == "auth_ok" for m in ws.sent)

    def test_auth_loop_retries_on_fail_then_succeeds(self):
        server = GameServer()
        ws = make_ws()
        call_count = 0

        async def _recv():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return json.dumps({"type": "auth", "action": "login",
                                   "username": "alice", "password": "bad"})
            return json.dumps({"type": "auth", "action": "login",
                                "username": "alice", "password": "good"})

        ws.recv = _recv
        with patch("server.game_server.db.authenticate", side_effect=[False, True]), \
             patch("server.game_server.db.get_rating", return_value=1200):
            result = run(server._auth_loop(ws, Color.WHITE))
        assert result is True
        assert call_count == 2

    def test_auth_loop_closes_on_wrong_message_type(self):
        server = GameServer()
        ws = make_ws()
        ws.recv = AsyncMock(return_value=json.dumps({"type": "join", "username": "x"}))
        result = run(server._auth_loop(ws, Color.WHITE))
        assert result is False
        ws.close.assert_called_once()

    def test_auth_loop_returns_false_on_disconnect(self):
        server = GameServer()
        ws = make_ws()
        ws.recv = AsyncMock(side_effect=Exception("dropped"))
        result = run(server._auth_loop(ws, Color.WHITE))
        assert result is False


# ---------------------------------------------------------------------------
# _on_connect — full handshake
# ---------------------------------------------------------------------------

class TestOnConnectHandshake:
    def test_assigned_sent_first(self):
        server = GameServer()
        ws = make_ws()
        server._start_game = AsyncMock()
        with patch_db_ok():
            run(server._on_connect(ws))
        assert ws.sent[0]["type"] == "assigned"
        assert ws.sent[0]["color"] == Color.WHITE.value

    def test_auth_ok_sent_after_assigned(self):
        server = GameServer()
        ws = make_ws()
        server._start_game = AsyncMock()
        with patch_db_ok():
            run(server._on_connect(ws))
        types = [m["type"] for m in ws.sent]
        assert types.index("assigned") < types.index("auth_ok")

    def test_username_stored_after_auth(self):
        server = GameServer()
        ws = make_ws()
        server._start_game = AsyncMock()
        with patch_db_ok(username="Alice"):
            run(server._on_connect(ws))
        assert server._usernames.get(Color.WHITE) == "Alice"

    def test_invalid_join_type_closes_connection(self):
        server = GameServer()
        ws = make_ws()
        _msgs = iter([
            json.dumps({"type": "auth", "action": "login", "username": "alice", "password": "x"}),
            json.dumps({"type": "move"}),
        ])
        async def _recv():
            return next(_msgs)
        ws.recv = _recv
        server._start_game = AsyncMock()
        with patch_db_ok():
            run(server._on_connect(ws))
        ws.close.assert_called()
        assert Color.WHITE not in server._clients

    def test_disconnect_during_game_cleans_up_client(self):
        server = GameServer()
        ws = make_ws()

        async def _anext(self):
            raise Exception("dropped")

        ws.__anext__ = _anext
        server._start_game = AsyncMock()
        with patch_db_ok():
            run(server._on_connect(ws))
        assert Color.WHITE not in server._clients


# ---------------------------------------------------------------------------
# _broadcast_rating_updates
# ---------------------------------------------------------------------------

class TestBroadcastRatingUpdates:
    def _server_after_game(self, winner="Alice", loser="Bob"):
        server = GameServer()
        ws_w, ws_b = make_ws(), make_ws()
        server._clients   = {Color.WHITE: ws_w, Color.BLACK: ws_b}
        server._usernames = {Color.WHITE: winner, Color.BLACK: loser}
        server._ratings   = {Color.WHITE: 1200, Color.BLACK: 1200}
        server._winner_name = winner
        return server, ws_w, ws_b

    def test_winner_receives_positive_delta(self):
        server, ws_w, _ = self._server_after_game()
        with patch("server.game_server.db.update_ratings", return_value=(16, -16)):
            run(server._broadcast_rating_updates())
        msg = next(m for m in ws_w.sent if m.get("type") == "rating_update")
        assert msg["delta"] > 0
        assert msg["new_rating"] == 1216

    def test_loser_receives_negative_delta(self):
        server, _, ws_b = self._server_after_game()
        with patch("server.game_server.db.update_ratings", return_value=(16, -16)):
            run(server._broadcast_rating_updates())
        msg = next(m for m in ws_b.sent if m.get("type") == "rating_update")
        assert msg["delta"] < 0
        assert msg["new_rating"] == 1184

    def test_no_update_when_winner_unknown(self):
        server, ws_w, ws_b = self._server_after_game()
        server._winner_name = "Ghost"
        with patch("server.game_server.db.update_ratings", return_value=(16, -16)):
            run(server._broadcast_rating_updates())
        assert not any(m.get("type") == "rating_update" for m in ws_w.sent)

    def test_no_update_when_only_one_player(self):
        server = GameServer()
        ws = make_ws()
        server._clients   = {Color.WHITE: ws}
        server._usernames = {Color.WHITE: "Alice"}
        server._ratings   = {Color.WHITE: 1200}
        server._winner_name = "Alice"
        with patch("server.game_server.db.update_ratings", return_value=(16, -16)):
            run(server._broadcast_rating_updates())
        assert not any(m.get("type") == "rating_update" for m in ws.sent)

    def test_failed_send_does_not_raise(self):
        server, ws_w, _ = self._server_after_game()

        async def _raise(data):
            raise Exception("gone")

        ws_w.send = _raise
        with patch("server.game_server.db.update_ratings", return_value=(16, -16)):
            run(server._broadcast_rating_updates())  # must not raise


# ---------------------------------------------------------------------------
# _start_game
# ---------------------------------------------------------------------------

class TestStartGame:
    def test_uses_stored_usernames(self):
        server = GameServer()
        server._usernames = {Color.BLACK: "Alice", Color.WHITE: "Bob"}
        with patch("server.game_server.load_board_csv", return_value=[["wK", "bK"]]), \
             patch("server.game_server.asyncio.create_task"):
            run(server._start_game())
        snap = server._game.get_game_snapshot()
        assert snap.black.name == "Alice"
        assert snap.white.name == "Bob"

    def test_defaults_when_no_username(self):
        server = GameServer()
        with patch("server.game_server.load_board_csv", return_value=[["wK", "bK"]]), \
             patch("server.game_server.asyncio.create_task"):
            run(server._start_game())
        snap = server._game.get_game_snapshot()
        assert snap.black.name == "Black"
        assert snap.white.name == "White"


# ---------------------------------------------------------------------------
# _handle_message
# ---------------------------------------------------------------------------

class TestHandleMessage:
    def _server_with_game(self):
        server = GameServer()
        with patch("server.game_server.load_board_csv", return_value=[["wR", ".", "bK"]]), \
             patch("server.game_server.asyncio.create_task"):
            run(server._start_game())
        ws = make_ws()
        server._clients[Color.WHITE] = ws
        return server, ws

    def test_move_schedules_move(self):
        server, _ = self._server_with_game()
        run(server._handle_message(
            json.dumps({"type": "move", "from": [0, 0], "to": [0, 1]}), Color.WHITE
        ))
        assert len(server._game.pending_moves) == 1

    def test_jump_schedules_jump(self):
        server, _ = self._server_with_game()
        run(server._handle_message(
            json.dumps({"type": "jump", "cell": [0, 0]}), Color.WHITE
        ))
        assert len(server._game.pending_jumps) == 1

    def test_legal_moves_sends_reply(self):
        server, ws = self._server_with_game()
        run(server._handle_message(
            json.dumps({"type": "legal_moves", "cell": [0, 0]}), Color.WHITE
        ))
        assert any(m.get("type") == "legal_moves" for m in ws.sent)

    def test_invalid_json_ignored(self):
        server, _ = self._server_with_game()
        run(server._handle_message("not json", Color.WHITE))

    def test_ignored_when_game_none(self):
        server = GameServer()
        run(server._handle_message(
            json.dumps({"type": "move", "from": [0, 0], "to": [0, 1]}), Color.WHITE
        ))

    def test_ignored_when_game_over(self):
        server, _ = self._server_with_game()
        server._game.is_game_over = True
        run(server._handle_message(
            json.dumps({"type": "move", "from": [0, 0], "to": [0, 1]}), Color.WHITE
        ))
        assert len(server._game.pending_moves) == 0

    def test_move_sets_game_start_time(self):
        server, _ = self._server_with_game()
        assert server._game_start_time == 0.0
        run(server._handle_message(
            json.dumps({"type": "move", "from": [0, 0], "to": [0, 1]}), Color.WHITE
        ))
        assert server._game_start_time > 0.0

    def test_jump_sets_game_start_time(self):
        server, _ = self._server_with_game()
        run(server._handle_message(
            json.dumps({"type": "jump", "cell": [0, 0]}), Color.WHITE
        ))
        assert server._game_start_time > 0.0


# ---------------------------------------------------------------------------
# _broadcast
# ---------------------------------------------------------------------------

class TestBroadcast:
    def test_sends_to_all_clients(self):
        server = GameServer()
        ws1, ws2 = make_ws(), make_ws()
        server._clients = {Color.WHITE: ws1, Color.BLACK: ws2}
        run(server._broadcast('{"type":"state"}'))
        assert len(ws1.sent) == 1
        assert len(ws2.sent) == 1

    def test_ignores_failed_client(self):
        server = GameServer()
        ws_ok = make_ws()
        ws_bad = make_ws()

        async def _raise(data):
            raise Exception("gone")

        ws_bad.send = _raise
        server._clients = {Color.WHITE: ws_ok, Color.BLACK: ws_bad}
        run(server._broadcast('{"type":"state"}'))
        assert len(ws_ok.sent) == 1


# ---------------------------------------------------------------------------
# _game_loop
# ---------------------------------------------------------------------------

class TestGameLoop:
    def _server_with_game(self):
        server = GameServer()
        with patch("server.game_server.load_board_csv", return_value=[["wR", "bK"]]), \
             patch("server.game_server.asyncio.create_task"):
            run(server._start_game())
        ws = make_ws()
        server._clients[Color.WHITE] = ws
        return server, ws

    def test_game_over_immediately_sends_final_state(self):
        server, ws = self._server_with_game()
        server._game.is_game_over = True
        with patch("server.game_server.db.update_ratings", return_value=(16, -16)):
            run(server._game_loop())
        assert any(m.get("game_over") is True for m in ws.sent)

    def test_game_over_inside_lock_sends_final_state(self):
        server, ws = self._server_with_game()
        original = server._game.execute_pending_moves

        def _set_over():
            original()
            server._game.is_game_over = True

        server._game.execute_pending_moves = _set_over
        with patch("server.game_server.db.update_ratings", return_value=(16, -16)):
            run(server._game_loop())
        assert any(m.get("game_over") is True for m in ws.sent)

    def test_loop_runs_ticks_then_stops(self):
        server, ws = self._server_with_game()
        tick_count = 0
        original_sleep = asyncio.sleep

        async def fast_sleep(delay):
            nonlocal tick_count
            tick_count += 1
            if tick_count >= 2:
                server._game.is_game_over = True
            await original_sleep(0)

        with patch("server.game_server.asyncio.sleep", fast_sleep), \
             patch("server.game_server.db.update_ratings", return_value=(16, -16)):
            run(server._game_loop())

        assert tick_count >= 1
        assert any(m.get("type") == "state" for m in ws.sent)
