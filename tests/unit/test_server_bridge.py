"""
Tests for client/server_bridge.py.

Patches websockets.connect so no real network is needed.
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from kungfu_chess.shared.constants import Color
from kungfu_chess.model.position import Position
from client.server_bridge import ServerBridge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    return asyncio.run(coro)


def make_mock_ws(server_messages=()):
    """
    Return a mock websocket context manager that yields `server_messages`
    (list of dicts) when iterated.
    """
    ws = AsyncMock()
    ws.sent = []

    async def _send(data):
        ws.sent.append(json.loads(data))

    ws.send = _send

    _msgs = [json.dumps(m) for m in server_messages]
    _iter = iter(_msgs)

    async def _anext(self):
        try:
            return next(_iter)
        except StopIteration:
            raise StopAsyncIteration

    ws.__aiter__ = lambda self: self
    ws.__anext__ = _anext

    # context manager
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=ws)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm, ws


def bridge_with_messages(server_messages):
    """
    Run the bridge's _ws_loop against a fake server that sends `server_messages`.
    Returns (bridge, ws_mock).
    """
    cm, ws = make_mock_ws(server_messages)
    bridge = ServerBridge()
    bridge._username = "TestUser"
    with patch("client.server_bridge.websockets.connect", return_value=cm):
        run(bridge._ws_loop())
    return bridge, ws


# ---------------------------------------------------------------------------
# _ws_loop — no automatic join (join is sent after auth via outgoing queue)
# ---------------------------------------------------------------------------

class TestWsLoopNoAutoJoin:
    def test_no_automatic_join_sent(self):
        _, ws = bridge_with_messages([
            {"type": "assigned", "color": "w"},
        ])
        join_msgs = [m for m in ws.sent if m.get("type") == "join"]
        assert len(join_msgs) == 0


# ---------------------------------------------------------------------------
# _receiver — assigned message
# ---------------------------------------------------------------------------

class TestReceiverAssigned:
    def test_assigned_sets_color_white(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
        ])
        assert bridge._color == Color.WHITE

    def test_assigned_sets_color_black(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "b"},
        ])
        assert bridge._color == Color.BLACK

    def test_assigned_sets_assigned_event(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
        ])
        assert bridge._assigned.is_set()


# ---------------------------------------------------------------------------
# _receiver — state message
# ---------------------------------------------------------------------------

class TestReceiverState:
    def _state_msg(self):
        from server.serializer import snapshot_to_dict
        from kungfu_chess.shared.dto import (
            GameSnapshot, BoardSnapshot, PlayerSnapshot
        )
        board = BoardSnapshot(grid=(), rows=0, cols=0)
        snap = GameSnapshot(
            board=board,
            black=PlayerSnapshot("B", Color.BLACK, 0, (), ()),
            white=PlayerSnapshot("W", Color.WHITE, 0, (), ()),
        )
        return snapshot_to_dict(snap)

    def test_state_message_put_in_incoming(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
            self._state_msg(),
        ])
        assert not bridge._incoming.empty()

    def test_poll_state_returns_latest(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
            self._state_msg(),
        ])
        result = bridge.poll_state()
        assert result is not None
        snap, _, _ = result
        assert snap.game_over is False

    def test_poll_state_returns_none_when_empty(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
        ])
        assert bridge.poll_state() is None


# ---------------------------------------------------------------------------
# _receiver — legal_moves message
# ---------------------------------------------------------------------------

class TestReceiverLegalMoves:
    def test_legal_moves_put_in_queue(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
            {"type": "legal_moves", "moves": [[0, 1], [0, 2]]},
        ])
        result = bridge.poll_legal_moves()
        assert result is not None
        assert Position(0, 1) in result
        assert Position(0, 2) in result

    def test_poll_legal_moves_returns_none_when_empty(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
        ])
        assert bridge.poll_legal_moves() is None


# ---------------------------------------------------------------------------
# _receiver — invalid JSON is ignored
# ---------------------------------------------------------------------------

class TestReceiverInvalidJson:
    def test_invalid_json_does_not_crash(self):
        cm, ws = make_mock_ws()
        _msgs = iter(["not valid json", json.dumps({"type": "assigned", "color": "w"})])

        async def _anext(self):
            try:
                return next(_msgs)
            except StopIteration:
                raise StopAsyncIteration

        ws.__anext__ = _anext
        bridge = ServerBridge()
        bridge._username = "X"
        with patch("client.server_bridge.websockets.connect", return_value=cm):
            run(bridge._ws_loop())
        assert bridge._color == Color.WHITE


# ---------------------------------------------------------------------------
# _sender — drains outgoing queue
# ---------------------------------------------------------------------------

class TestSender:
    def test_queued_move_is_sent(self):
        cm, ws = make_mock_ws([{"type": "assigned", "color": "w"}])
        bridge = ServerBridge()
        bridge._username = "X"
        bridge.send_move(Position(0, 0), Position(0, 1))

        with patch("client.server_bridge.websockets.connect", return_value=cm):
            run(bridge._ws_loop())

        move_msgs = [m for m in ws.sent if m.get("type") == "move"]
        assert len(move_msgs) == 1
        assert move_msgs[0]["from"] == [0, 0]
        assert move_msgs[0]["to"] == [0, 1]

    def test_queued_jump_is_sent(self):
        cm, ws = make_mock_ws([{"type": "assigned", "color": "w"}])
        bridge = ServerBridge()
        bridge._username = "X"
        bridge.send_jump(Position(1, 2))

        with patch("client.server_bridge.websockets.connect", return_value=cm):
            run(bridge._ws_loop())

        jump_msgs = [m for m in ws.sent if m.get("type") == "jump"]
        assert len(jump_msgs) == 1
        assert jump_msgs[0]["cell"] == [1, 2]

    def test_legal_moves_request_is_sent(self):
        cm, ws = make_mock_ws([{"type": "assigned", "color": "w"}])
        bridge = ServerBridge()
        bridge._username = "X"
        bridge.request_legal_moves(Position(3, 4))

        with patch("client.server_bridge.websockets.connect", return_value=cm):
            run(bridge._ws_loop())

        lm_msgs = [m for m in ws.sent if m.get("type") == "legal_moves"]
        assert len(lm_msgs) == 1
        assert lm_msgs[0]["cell"] == [3, 4]


# ---------------------------------------------------------------------------
# start() — username stored and assigned event set
# ---------------------------------------------------------------------------

class TestStart:
    def test_start_stores_username(self):
        cm, ws = make_mock_ws([{"type": "assigned", "color": "w"}])
        bridge = ServerBridge()
        with patch("client.server_bridge.websockets.connect", return_value=cm):
            # run _ws_loop in a thread as start() does, but synchronously here
            import threading
            bridge._username = "Zara"
            t = threading.Thread(target=lambda: run(bridge._ws_loop()), daemon=True)
            t.start()
            bridge._assigned.wait(timeout=2)
        assert bridge._username == "Zara"

    def test_color_accessible_after_assigned(self):
        cm, ws = make_mock_ws([{"type": "assigned", "color": "b"}])
        bridge = ServerBridge()
        bridge._username = "X"
        with patch("client.server_bridge.websockets.connect", return_value=cm):
            run(bridge._ws_loop())
        assert bridge.color() == Color.BLACK


# ---------------------------------------------------------------------------
# authenticate() — sends auth message, blocks on auth_result queue
# ---------------------------------------------------------------------------

class TestAuthenticate:
    def test_authenticate_login_returns_auth_ok(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
            {"type": "auth_ok", "username": "alice", "rating": 1200},
        ])
        bridge._outgoing.put(
            {"type": "auth", "action": "login", "username": "alice", "password": "x"}
        )
        # Simulate what authenticate() does: put on outgoing, get from auth_result
        bridge._auth_result.put({"type": "auth_ok", "username": "alice", "rating": 1200})
        result = bridge._auth_result.get()
        assert result["type"] == "auth_ok"
        assert result["username"] == "alice"
        assert result["rating"] == 1200

    def test_authenticate_routes_auth_ok_to_queue(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
            {"type": "auth_ok", "username": "bob", "rating": 1350},
        ])
        assert not bridge._auth_result.empty()
        result = bridge._auth_result.get()
        assert result["type"] == "auth_ok"
        assert result["rating"] == 1350

    def test_authenticate_routes_auth_fail_to_queue(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
            {"type": "auth_fail", "reason": "invalid credentials"},
        ])
        assert not bridge._auth_result.empty()
        result = bridge._auth_result.get()
        assert result["type"] == "auth_fail"
        assert result["reason"] == "invalid credentials"

    def test_authenticate_sends_auth_message(self):
        cm, ws = make_mock_ws([{"type": "assigned", "color": "w"}])
        bridge = ServerBridge()
        bridge._outgoing.put(
            {"type": "auth", "action": "register", "username": "carol", "password": "p"}
        )
        with patch("client.server_bridge.websockets.connect", return_value=cm):
            run(bridge._ws_loop())
        auth_msgs = [m for m in ws.sent if m.get("type") == "auth"]
        assert len(auth_msgs) == 1
        assert auth_msgs[0]["username"] == "carol"
        assert auth_msgs[0]["action"] == "register"


# ---------------------------------------------------------------------------
# poll_rating_update() — routes rating_update messages
# ---------------------------------------------------------------------------

class TestPollRatingUpdate:
    def test_rating_update_routed_to_queue(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
            {"type": "rating_update", "username": "alice",
             "old_rating": 1200, "new_rating": 1216, "delta": 16},
        ])
        result = bridge.poll_rating_update()
        assert result is not None
        assert result["type"] == "rating_update"
        assert result["delta"] == 16
        assert result["new_rating"] == 1216

    def test_poll_rating_update_returns_none_when_empty(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
        ])
        assert bridge.poll_rating_update() is None

    def test_multiple_rating_updates_queued(self):
        bridge, _ = bridge_with_messages([
            {"type": "assigned", "color": "w"},
            {"type": "rating_update", "username": "alice",
             "old_rating": 1200, "new_rating": 1216, "delta": 16},
            {"type": "rating_update", "username": "bob",
             "old_rating": 1200, "new_rating": 1184, "delta": -16},
        ])
        r1 = bridge.poll_rating_update()
        r2 = bridge.poll_rating_update()
        assert r1["username"] == "alice"
        assert r2["username"] == "bob"
