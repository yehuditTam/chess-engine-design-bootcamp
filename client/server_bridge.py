"""
ServerBridge — decouples the asyncio WebSocket layer from the synchronous OpenCV loop.

The OpenCV loop (main thread) calls:
    bridge.send_move(start, end)   — queues a move command
    bridge.send_jump(cell)         — queues a jump command
    bridge.poll_state()            — returns latest (GameSnapshot, game_over) or None

A background asyncio thread runs the WebSocket connection, drains outgoing
commands, and puts incoming state messages into the incoming queue.
"""

import asyncio
import json
import queue
import threading
import websockets
from kungfu_chess.model.position import Position
from kungfu_chess.shared.constants import Color
from server.serializer import dict_to_snapshot

SERVER_URL = "ws://localhost:8765"


class ServerBridge:
    def __init__(self):
        self._outgoing: queue.Queue = queue.Queue()  # commands main→ws
        self._incoming: queue.Queue = queue.Queue()  # state    ws→main
        self._legal_moves: queue.Queue = queue.Queue()  # legal_moves replies
        self._events: queue.Queue = queue.Queue()  # pub/sub events
        self._color: Color | None = None
        self._connected = threading.Event()           # set when WS is open
        self._assigned = threading.Event()            # set when color is received
        self._thread = threading.Thread(target=self._run_loop, daemon=True)

    # ------------------------------------------------------------------
    # Public API — called from the main (OpenCV) thread
    # ------------------------------------------------------------------

    def start(self, username: str = "Player"):
        """Start the background WebSocket thread. Blocks until color is assigned."""
        self._username = username
        self._thread.start()
        self._assigned.wait()         # wait until server sends "assigned"

    def color(self) -> Color | None:
        """Return the color assigned by the server (WHITE or BLACK)."""
        return self._color

    def send_move(self, start: Position, end: Position):
        """Queue a move command to be sent to the server."""
        self._outgoing.put({"type": "move", "from": list(start), "to": list(end)})

    def send_jump(self, cell: Position):
        """Queue a jump command to be sent to the server."""
        self._outgoing.put({"type": "jump", "cell": list(cell)})

    def request_legal_moves(self, cell: Position):
        """Send a legal_moves request to the server for the piece at the given cell."""
        self._outgoing.put({"type": "legal_moves", "cell": [cell.row, cell.col]})

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

    def poll_state(self):
        """
        Return the most recent (GameSnapshot, game_over) received from the server,
        or None if no new state has arrived since the last call.
        Drains all queued states and returns only the latest.
        """
        latest = None
        while not self._incoming.empty():
            try:
                latest = self._incoming.get_nowait()
            except queue.Empty:
                break
        return latest

    # ------------------------------------------------------------------
    # Background thread — runs the asyncio event loop
    # ------------------------------------------------------------------

    def _run_loop(self):
        asyncio.run(self._ws_loop())

    async def _ws_loop(self):
        async with websockets.connect(SERVER_URL) as ws:
            self._connected.set()           # unblock start()
            await ws.send(json.dumps({"type": "join", "username": self._username}))
            sender_task = asyncio.create_task(self._sender(ws))
            await asyncio.sleep(0)          # let sender drain outgoing queue first
            try:
                await self._receiver(ws)
            finally:
                sender_task.cancel()
                try:
                    await sender_task
                except asyncio.CancelledError:
                    pass

    # ------------------------------------------------------------------
    # Receive state messages from the server
    # ------------------------------------------------------------------

    async def _receiver(self, ws):
        async for raw in ws:
            try:
                d = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if d["type"] == "assigned":
                self._color = Color(d["color"])
                self._assigned.set()    # unblock start()
            elif d["type"] == "state":
                snap, game_over, game_start_time, winner_name = dict_to_snapshot(d)
                self._incoming.put((snap, game_over, game_start_time, winner_name))
            elif d["type"] == "legal_moves":
                moves = [Position(*m) for m in d["moves"]]
                self._legal_moves.put(moves)
            elif d["type"] in ("scores_updated", "move_logged", "sound", "animation"):
                self._events.put(d)

    # ------------------------------------------------------------------
    # Send queued commands to the server
    # ------------------------------------------------------------------

    async def _sender(self, ws):
        while True:
            # check outgoing queue without blocking the event loop
            try:
                msg = self._outgoing.get_nowait()
                await ws.send(json.dumps(msg))
            except queue.Empty:
                await asyncio.sleep(0.01)
