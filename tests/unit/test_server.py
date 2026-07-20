"""
Tests for server/game_server.py.

Uses unittest.mock to replace websockets so no real network is needed.
All async helpers run via pytest-asyncio (or asyncio.run in sync wrappers).
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from kungfu_chess.shared.constants import Color
from server.game_server import GameServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_ws(messages=()):
    """
    Return a mock websocket that yields `messages` (list of dicts) when
    iterated, and records everything sent via ws.send().
    """
    ws = AsyncMock()
    ws.sent = []

    async def _send(data):
        ws.sent.append(json.loads(data))

    ws.send = _send

    # __aiter__ / __anext__ so `async for raw in ws` works
    _iter = iter([json.dumps(m) for m in messages])

    async def _anext(self):
        try:
            return next(_iter)
        except StopIteration:
            raise StopAsyncIteration

    ws.__aiter__ = lambda self: self
    ws.__anext__ = _anext
    ws.close = AsyncMock()
    ws.recv = AsyncMock(return_value=json.dumps({"type": "join", "username": "Alice"}))
    return ws


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# _assign_color
# ---------------------------------------------------------------------------

class TestAssignColor:
    def test_first_client_gets_white(self):
        server = GameServer()
        ws = make_ws()
        color = run(server._assign_color(ws))
        assert color == Color.WHITE

    def test_second_client_gets_black(self):
        server = GameServer()
        ws1, ws2 = make_ws(), make_ws()
        run(server._assign_color(ws1))
        color = run(server._assign_color(ws2))
        assert color == Color.BLACK

    def test_third_client_gets_none(self):
        server = GameServer()
        run(server._assign_color(make_ws()))
        run(server._assign_color(make_ws()))
        color = run(server._assign_color(make_ws()))
        assert color is None


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
# _on_connect — join handshake
# ---------------------------------------------------------------------------

class TestOnConnectJoin:
    def test_valid_join_stores_username(self):
        server = GameServer()
        ws = make_ws()
        ws.recv = AsyncMock(return_value=json.dumps({"type": "join", "username": "Bob"}))
        # patch _start_game so we don't need a real board file
        server._start_game = AsyncMock()
        run(server._on_connect(ws))
        assert server._usernames.get(Color.WHITE) == "Bob"

    def test_invalid_join_type_closes_connection(self):
        server = GameServer()
        ws = make_ws()
        ws.recv = AsyncMock(return_value=json.dumps({"type": "move"}))
        server._start_game = AsyncMock()
        run(server._on_connect(ws))
        ws.close.assert_called_once()
        assert Color.WHITE not in server._clients

    def test_recv_exception_removes_client(self):
        server = GameServer()
        ws = make_ws()
        ws.recv = AsyncMock(side_effect=Exception("disconnected"))
        server._start_game = AsyncMock()
        run(server._on_connect(ws))
        assert Color.WHITE not in server._clients

    def test_assigned_message_sent_before_join(self):
        server = GameServer()
        ws = make_ws()
        ws.recv = AsyncMock(return_value=json.dumps({"type": "join", "username": "X"}))
        server._start_game = AsyncMock()
        run(server._on_connect(ws))
        assert ws.sent[0]["type"] == "assigned"
        assert ws.sent[0]["color"] == Color.WHITE.value

    def test_missing_username_defaults_to_color_name(self):
        server = GameServer()
        ws = make_ws()
        ws.recv = AsyncMock(return_value=json.dumps({"type": "join"}))
        server._start_game = AsyncMock()
        run(server._on_connect(ws))
        assert server._usernames.get(Color.WHITE) == Color.WHITE.name


# ---------------------------------------------------------------------------
# _start_game — uses stored usernames
# ---------------------------------------------------------------------------

class TestStartGame:
    def test_start_game_uses_stored_usernames(self):
        server = GameServer()
        server._usernames = {Color.BLACK: "Alice", Color.WHITE: "Bob"}
        board = [['wK', 'bK']]
        with patch("server.game_server.load_board_csv", return_value=board), \
             patch("server.game_server.asyncio.create_task"):
            run(server._start_game())
        snap = server._game.get_game_snapshot()
        assert snap.black.name == "Alice"
        assert snap.white.name == "Bob"

    def test_start_game_defaults_when_no_username(self):
        server = GameServer()
        board = [['wK', 'bK']]
        with patch("server.game_server.load_board_csv", return_value=board), \
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
        board = [['wR', '.', 'bK']]
        with patch("server.game_server.load_board_csv", return_value=board), \
             patch("server.game_server.asyncio.create_task"):
            run(server._start_game())
        ws = make_ws()
        server._clients[Color.WHITE] = ws
        return server, ws

    def test_move_message_schedules_move(self):
        server, _ = self._server_with_game()
        msg = json.dumps({"type": "move", "from": [0, 0], "to": [0, 1]})
        run(server._handle_message(msg, Color.WHITE))
        assert len(server._game.pending_moves) == 1

    def test_jump_message_schedules_jump(self):
        server, _ = self._server_with_game()
        msg = json.dumps({"type": "jump", "cell": [0, 0]})
        run(server._handle_message(msg, Color.WHITE))
        assert len(server._game.pending_jumps) == 1

    def test_legal_moves_message_sends_reply(self):
        server, ws = self._server_with_game()
        msg = json.dumps({"type": "legal_moves", "cell": [0, 0]})
        run(server._handle_message(msg, Color.WHITE))
        assert any(m.get("type") == "legal_moves" for m in ws.sent)

    def test_invalid_json_is_ignored(self):
        server, _ = self._server_with_game()
        run(server._handle_message("not json", Color.WHITE))  # should not raise

    def test_message_ignored_when_game_is_none(self):
        server = GameServer()
        msg = json.dumps({"type": "move", "from": [0, 0], "to": [0, 1]})
        run(server._handle_message(msg, Color.WHITE))  # no crash

    def test_message_ignored_when_game_over(self):
        server, _ = self._server_with_game()
        server._game.is_game_over = True
        msg = json.dumps({"type": "move", "from": [0, 0], "to": [0, 1]})
        run(server._handle_message(msg, Color.WHITE))
        assert len(server._game.pending_moves) == 0

    def test_legal_moves_no_ws_for_color(self):
        server, _ = self._server_with_game()
        server._clients.pop(Color.WHITE, None)
        msg = json.dumps({"type": "legal_moves", "cell": [0, 0]})
        run(server._handle_message(msg, Color.WHITE))  # should not raise


# ---------------------------------------------------------------------------
# _broadcast
# ---------------------------------------------------------------------------

class TestBroadcast:
    def test_broadcast_sends_to_all_clients(self):
        server = GameServer()
        ws1, ws2 = make_ws(), make_ws()
        server._clients = {Color.WHITE: ws1, Color.BLACK: ws2}
        run(server._broadcast('{"type":"state"}'))
        assert len(ws1.sent) == 1
        assert len(ws2.sent) == 1

    def test_broadcast_ignores_failed_client(self):
        server = GameServer()
        ws_ok = make_ws()
        ws_bad = make_ws()

        async def _raise(data):
            raise Exception("gone")

        ws_bad.send = _raise
        server._clients = {Color.WHITE: ws_ok, Color.BLACK: ws_bad}
        run(server._broadcast('{"type":"state"}'))  # should not raise
        assert len(ws_ok.sent) == 1


# ---------------------------------------------------------------------------
# _game_loop
# ---------------------------------------------------------------------------

class TestGameLoop:
    def test_game_loop_broadcasts_and_stops_on_game_over(self):
        server = GameServer()
        board = [['wR', 'bK']]
        with patch("server.game_server.load_board_csv", return_value=board), \
             patch("server.game_server.asyncio.create_task"):
            run(server._start_game())

        ws = make_ws()
        server._clients[Color.WHITE] = ws

        # Force game over immediately
        server._game.is_game_over = True
        run(server._game_loop())
        # Final game-over state must be broadcast
        assert any(m.get("game_over") is True for m in ws.sent)

    def test_game_loop_runs_tick_then_stops(self):
        server = GameServer()
        board = [['wR', 'bK']]
        with patch("server.game_server.load_board_csv", return_value=board), \
             patch("server.game_server.asyncio.create_task"):
            run(server._start_game())

        ws = make_ws()
        server._clients[Color.WHITE] = ws

        tick_count = 0
        original_sleep = asyncio.sleep

        async def fast_sleep(delay):
            nonlocal tick_count
            tick_count += 1
            if tick_count >= 2:
                server._game.is_game_over = True
            await original_sleep(0)

        with patch("server.game_server.asyncio.sleep", fast_sleep):
            run(server._game_loop())

        assert tick_count >= 1
        assert any(m.get("type") == "state" for m in ws.sent)
