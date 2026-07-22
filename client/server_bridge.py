"""ServerBridge — decouples the asyncio WebSocket layer from the synchronous OpenCV loop."""

import asyncio
import json
import queue
import threading

import websockets
from kungfu_chess.model.position import Position
from kungfu_chess.shared.constants import Color
from enum import Enum

SERVER_URL = "ws://localhost:8765"


class MsgType(str, Enum):
    assigned       = "assigned"
    auth_ok        = "auth_ok"
    auth_fail      = "auth_fail"
    state          = "state"
    legal_moves    = "legal_moves"
    rating_update  = "rating_update"
    event          = "event"
    scores_updated = "scores_updated"
    move_logged    = "move_logged"
    sound          = "sound"
    animation      = "animation"


_MSG_HANDLERS: dict[MsgType, str] = {
    MsgType.assigned:       "_handle_assigned",
    MsgType.auth_ok:        "_handle_auth",
    MsgType.auth_fail:      "_handle_auth",
    MsgType.state:          "_handle_state",
    MsgType.legal_moves:    "_handle_legal_moves",
    MsgType.rating_update:  "_handle_rating_update",
    MsgType.event:          "_handle_event",
    MsgType.scores_updated: "_handle_event",
    MsgType.move_logged:    "_handle_event",
    MsgType.sound:          "_handle_event",
    MsgType.animation:      "_handle_event",
}


class ServerBridge:

    # ------------------------------------------------------------------ #
    #  Construction                                                        #
    # ------------------------------------------------------------------ #

    def __init__(self):
        self._outgoing: queue.Queue = queue.Queue()       # commands main→ws
        self._incoming: queue.Queue = queue.Queue()       # state    ws→main
        self._legal_moves: queue.Queue = queue.Queue()    # legal_moves replies
        self._events: queue.Queue = queue.Queue()         # pub/sub events
        self._auth_result: queue.Queue = queue.Queue()    # auth_ok / auth_fail
        self._rating_updates: queue.Queue = queue.Queue()  # rating_update messages
        self._color: Color | None = None
        self._connected = threading.Event()               # set when WS is open
        self._assigned = threading.Event()                # set when color is received
        self._thread = threading.Thread(target=self._run_loop, daemon=True)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def start(self):
        """Start the background WebSocket thread. Blocks until color is assigned."""
        self._thread.start()
        self._assigned.wait()

    def color(self) -> Color | None:
        """Return the color assigned by the server (WHITE or BLACK)."""
        return self._color

    def authenticate(self, username: str, password: str, action: str = "login") -> dict:
        """Send auth and block until auth_ok or auth_fail. Returns the response dict."""
        self._outgoing.put({"type": "auth", "action": action,
                            "username": username, "password": password})
        return self._auth_result.get()

    def send_join(self, username: str):
        """Queue a join message after successful auth."""
        self._outgoing.put({"type": "join", "username": username})

    def send_move(self, start: Position, end: Position):
        """Queue a move command to be sent to the server."""
        self._outgoing.put({"type": "move", "from": list(start), "to": list(end)})

    def send_jump(self, cell: Position):
        """Queue a jump command to be sent to the server."""
        self._outgoing.put({"type": "jump", "cell": list(cell)})

    def request_legal_moves(self, cell: Position):
        """Send a legal_moves request to the server for the piece at the given cell."""
        self._outgoing.put({"type": "legal_moves", "cell": [cell.row, cell.col]})

    def poll_state(self):
        """Return the latest (GameSnapshot, game_start_time, winner_name), or None."""
        latest = None
        while not self._incoming.empty():
            try:
                latest = self._incoming.get_nowait()
            except queue.Empty:
                break
        return latest

    def poll_legal_moves(self):
        """Return the latest legal_moves reply from the server, or None if none available."""
        try:
            return self._legal_moves.get_nowait()
        except queue.Empty:
            return None

    def poll_events(self) -> list[dict]:
        """Return all queued pub/sub event dicts and clear the queue."""
        events = []
        while not self._events.empty():
            try:
                events.append(self._events.get_nowait())
            except queue.Empty:
                break
        return events

    def poll_rating_update(self) -> dict | None:
        """Return a rating_update dict if one has arrived, else None."""
        try:
            return self._rating_updates.get_nowait()
        except queue.Empty:
            return None

    # ------------------------------------------------------------------ #
    #  Message handlers                                                    #
    # ------------------------------------------------------------------ #

    def _handle_assigned(self, d):
        self._color = Color(d["color"])
        self._assigned.set()

    def _handle_auth(self, d):
        self._auth_result.put(d)

    def _handle_state(self, d):
        from server.serializer import dict_to_snapshot
        self._incoming.put(dict_to_snapshot(d))

    def _handle_legal_moves(self, d):
        self._legal_moves.put([Position(*m) for m in d["moves"]])

    def _handle_rating_update(self, d):
        self._rating_updates.put(d)

    def _handle_event(self, d):
        self._events.put(d)

    # ------------------------------------------------------------------ #
    #  WebSocket internals                                                 #
    # ------------------------------------------------------------------ #

    def _run_loop(self):
        asyncio.run(self._ws_loop())

    async def _ws_loop(self):
        async with websockets.connect(SERVER_URL) as ws:
            self._connected.set()
            sender_task = asyncio.create_task(self._sender(ws))
            await asyncio.sleep(0)
            try:
                await self._receiver(ws)
            finally:
                sender_task.cancel()
                try:
                    await sender_task
                except asyncio.CancelledError:
                    pass

    async def _receiver(self, ws):
        async for raw in ws:
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue
            try:
                msg_type = MsgType(d["type"])
            except ValueError:
                continue
            getattr(self, _MSG_HANDLERS[msg_type])(d)

    async def _sender(self, ws):
        while True:
            try:
                msg = self._outgoing.get_nowait()
                await ws.send(json.dumps(msg))
            except queue.Empty:
                await asyncio.sleep(0.01)
