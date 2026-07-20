"""
WebSocket game server.

Responsibilities:
  - Accept exactly 2 player connections (first = WHITE, second = BLACK)
  - Run the GameEngine tick every 30 ms and broadcast state to both clients
  - Route move/jump commands from each client to the GameEngine
  - Reject or queue extra connections until a slot is free

Run with:
    python -m server.game_server
"""

import asyncio
import json
import logging
import time as _time
from kungfu_chess.realtime.game_engine import GameEngine
from kungfu_chess.io.board_parser import load_board_csv
from kungfu_chess.model.player import Player
from kungfu_chess.shared.constants import Color
from kungfu_chess.shared.bus import EventBus, EventType
from server.serializer import snapshot_to_dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SERVER] %(message)s")
log = logging.getLogger(__name__)

HOST = "localhost"
PORT = 8765
TICK_MS = 30
BOARD_CSV = "assets/board.csv"


class GameServer:
    def __init__(self):
        self._clients: dict[Color, object] = {}
        self._usernames: dict[Color, str] = {}
        self._game: GameEngine | None = None
        self._lock = asyncio.Lock()
        self._pending_events: list = []
        self._game_start_time = 0.0
        self._winner_name = ""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run(self):
        import websockets
        log.info(f"Listening on ws://{HOST}:{PORT}")
        async with websockets.serve(self._on_connect, HOST, PORT):
            await asyncio.Future()

    # ------------------------------------------------------------------
    # Connection handler
    # ------------------------------------------------------------------

    async def _on_connect(self, ws):
        color = await self._assign_color(ws)
        if color is None:
            await ws.send(json.dumps({"type": "error", "reason": "server_full"}))
            await ws.close()
            return

        log.info(f"{color.name} connected")
        await ws.send(json.dumps({"type": "assigned", "color": color.value}))

        try:
            raw = await ws.recv()
            msg = json.loads(raw)
            if msg.get("type") != "join":
                await ws.close()
                self._clients.pop(color, None)
                return
            self._usernames[color] = msg.get("username", color.name)
        except Exception:
            self._clients.pop(color, None)
            return

        if len(self._clients) == 2:
            await self._start_game()

        try:
            async for raw in ws:
                await self._handle_message(raw, color)
        except Exception as e:
            log.warning(f"{color.name} disconnected: {e}")
        finally:
            self._clients.pop(color, None)
            log.info(f"{color.name} left")

    # ------------------------------------------------------------------
    # Assign colors
    # ------------------------------------------------------------------

    async def _assign_color(self, ws) -> Color | None:
        async with self._lock:
            if Color.WHITE not in self._clients:
                self._clients[Color.WHITE] = ws
                return Color.WHITE
            if Color.BLACK not in self._clients:
                self._clients[Color.BLACK] = ws
                return Color.BLACK
            return None

    # ------------------------------------------------------------------
    # Start game
    # ------------------------------------------------------------------

    async def _start_game(self):
        rows = load_board_csv(BOARD_CSV)
        bus = EventBus()
        self._pending_events = []
        self._game_start_time = 0.0
        self._winner_name = ""

        # Collect winner name on game over
        bus.subscribe(
            EventType.GAME_OVER,
            lambda winner_color, **_: setattr(
                self, '_winner_name',
                self._usernames.get(
                    Color.BLACK if winner_color == Color.BLACK else Color.WHITE,
                    winner_color.name
                )
            )
        )

        # Queue every bus event for broadcast to clients
        for ev_name, ev_type in (
            ("game_started",    EventType.GAME_STARTED),
            ("piece_moved",     EventType.PIECE_MOVED),
            ("piece_captured",  EventType.PIECE_CAPTURED),
            ("piece_jumped",    EventType.PIECE_JUMPED),
            ("score_updated",   EventType.SCORE_UPDATED),
            ("move_logged",     EventType.MOVE_LOGGED),
            ("game_over",       EventType.GAME_OVER),
        ):
            def _make_handler(name):
                def _h(**_kw):
                    self._pending_events.append({"type": "event", "name": name})
                return _h
            bus.subscribe(ev_type, _make_handler(ev_name))

        self._game = GameEngine(
            rows,
            black=Player(self._usernames.get(Color.BLACK, "Black"), Color.BLACK),
            white=Player(self._usernames.get(Color.WHITE, "White"), Color.WHITE),
            bus=bus,
        )
        log.info("Game started")
        asyncio.create_task(self._game_loop())

    # ------------------------------------------------------------------
    # Game loop
    # ------------------------------------------------------------------

    async def _game_loop(self):
        while self._game is not None and not self._game.is_game_over:
            async with self._lock:
                self._game.execute_pending_moves()
                if self._game.is_game_over:
                    break
                snap = self._game.get_game_snapshot()
                elapsed = (
                    _time.time() - self._game_start_time
                    if self._game_start_time > 0.0 else 0.0
                )
                state_msg = json.dumps(snapshot_to_dict(snap, False, elapsed, ""))
                events, self._pending_events = self._pending_events, []

            await self._broadcast(state_msg)
            for ev in events:
                await self._broadcast(json.dumps(ev))
            await asyncio.sleep(TICK_MS / 1000)

        # final game-over state
        if self._game is not None:
            snap = self._game.get_game_snapshot()
            elapsed = (
                _time.time() - self._game_start_time
                if self._game_start_time > 0.0 else 0.0
            )
            state_msg = json.dumps(snapshot_to_dict(snap, True, elapsed, self._winner_name))
            events, self._pending_events = self._pending_events, []
            await self._broadcast(state_msg)
            for ev in events:
                await self._broadcast(json.dumps(ev))
        log.info("Game over — loop stopped")

    # ------------------------------------------------------------------
    # Handle client messages
    # ------------------------------------------------------------------

    async def _handle_message(self, raw: str, color: Color):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        if self._game is None or self._game.is_game_over:
            return

        from kungfu_chess.model.position import Position
        async with self._lock:
            if msg["type"] == "move":
                fr, to = msg["from"], msg["to"]
                if self._game_start_time == 0.0:
                    self._game_start_time = _time.time()
                self._game.request_move(Position(*fr), Position(*to))
            elif msg["type"] == "jump":
                cell = msg["cell"]
                if self._game_start_time == 0.0:
                    self._game_start_time = _time.time()
                self._game.handle_jump(Position(*cell))
            elif msg["type"] == "legal_moves":
                cell = msg["cell"]
                moves = self._game.get_legal_moves(Position(*cell))
                ws = self._clients.get(color)
                if ws:
                    reply = json.dumps({
                        "type": "legal_moves",
                        "cell": cell,
                        "moves": [[p.row, p.col] for p in moves],
                    })
                    await ws.send(reply)

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def _broadcast(self, msg: str):
        for ws in list(self._clients.values()):
            try:
                await ws.send(msg)
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(GameServer().run())
