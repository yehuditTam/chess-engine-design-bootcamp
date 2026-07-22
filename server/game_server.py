import asyncio
import json
import logging
from kungfu_chess.realtime.game_engine import GameEngine
from kungfu_chess.io.board_parser import load_board_csv
from kungfu_chess.model.player import Player
from kungfu_chess.shared.constants import Color
from kungfu_chess.shared.bus import EventBus, EventType
from kungfu_chess.model.position import Position
from server.serializer import snapshot_to_dict
import server.db as db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SERVER] %(message)s")
log = logging.getLogger(__name__)

HOST = "localhost"
PORT = 8765
TICK_MS = 30
BOARD_CSV = "assets/board.csv"


class GameServer:
    _EVENT_NAMES = {
        EventType.GAME_STARTED:   "game_started",
        EventType.PIECE_MOVED:    "piece_moved",
        EventType.PIECE_CAPTURED: "piece_captured",
        EventType.PIECE_JUMPED:   "piece_jumped",
        EventType.SCORE_UPDATED:  "score_updated",
        EventType.MOVE_LOGGED:    "move_logged",
        EventType.GAME_OVER:      "game_over",
    }

    def __init__(self):
        self._clients:   dict[Color, object] = {}
        self._usernames: dict[Color, str]    = {}
        self._ratings:   dict[Color, int]    = {}
        self._game:      GameEngine | None   = None
        self._lock = asyncio.Lock()
        self._pending_events: list = []
        self._winner_name = ""

    async def run(self) -> None:
        import websockets
        log.info(f"Listening on ws://{HOST}:{PORT}")
        async with websockets.serve(self._on_connect, HOST, PORT):
            await asyncio.Future()

    # --- connection lifecycle ---

    async def _on_connect(self, ws) -> None:
        color = await self._assign_color(ws)
        if color is None:
            await ws.send(json.dumps({"type": "error", "reason": "server_full"}))
            await ws.close()
            return

        log.info(f"{color.name} connected")
        await ws.send(json.dumps({"type": "assigned", "color": color.value}))

        if not await self._auth_loop(ws, color):
            return
        if not await self._await_join(ws, color):
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

    async def _assign_color(self, ws) -> Color | None:
        async with self._lock:
            if Color.WHITE not in self._clients:
                self._clients[Color.WHITE] = ws
                return Color.WHITE
            if Color.BLACK not in self._clients:
                self._clients[Color.BLACK] = ws
                return Color.BLACK
            return None

    async def _auth_loop(self, ws, color: Color) -> bool:
        """Loops until the client authenticates successfully. Returns False on disconnect."""
        try:
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("type") != "auth":
                    await ws.close()
                    self._clients.pop(color, None)
                    return False
                response = self._process_auth(msg, color)
                await ws.send(json.dumps(response))
                if response["type"] == "auth_ok":
                    return True
        except Exception:
            self._clients.pop(color, None)
            return False

    def _process_auth(self, msg: dict, color: Color) -> dict:
        """Validates credentials and returns auth_ok or auth_fail."""
        username = msg.get("username", "").strip()
        password = msg.get("password", "")
        action   = msg.get("action", "login")
        if not username:
            return {"type": "auth_fail", "reason": "username required"}
        if action == "register":
            if not db.register(username, password):
                return {"type": "auth_fail", "reason": "username taken"}
        elif not db.authenticate(username, password):
            return {"type": "auth_fail", "reason": "invalid credentials"}
        rating = db.get_rating(username)
        self._usernames[color] = username
        self._ratings[color]   = rating
        return {"type": "auth_ok", "username": username, "rating": rating}

    async def _await_join(self, ws, color: Color) -> bool:
        """Waits for the join message after auth. Returns False on failure."""
        try:
            msg = json.loads(await ws.recv())
            if msg.get("type") != "join":
                await ws.close()
                self._clients.pop(color, None)
                return False
            return True
        except Exception:
            self._clients.pop(color, None)
            return False

    # --- game lifecycle ---

    async def _start_game(self) -> None:
        rows = load_board_csv(BOARD_CSV)
        bus = EventBus()
        self._pending_events = []
        self._winner_name = ""
        self._subscribe_bus(bus)
        self._game = GameEngine(
            rows,
            black=Player(self._usernames.get(Color.BLACK, "Black"), Color.BLACK),
            white=Player(self._usernames.get(Color.WHITE, "White"), Color.WHITE),
            bus=bus,
        )
        log.info("Game started")
        asyncio.create_task(self._game_loop())

    def _subscribe_bus(self, bus: EventBus) -> None:
        """Wires bus events to winner tracking and client broadcast queue."""
        bus.subscribe(EventType.GAME_OVER, self._on_game_over)
        for ev_type, name in self._EVENT_NAMES.items():
            bus.subscribe(
                ev_type,
                lambda name=name, **_: self._pending_events.append({"type": "event", "name": name})
            )

    def _on_game_over(self, winner_color, **_) -> None:
        self._winner_name = self._usernames.get(winner_color, winner_color.name)

    async def _game_loop(self) -> None:
        while self._game is not None and not self._game.is_game_over:
            async with self._lock:
                self._game.execute_pending_moves()
                if self._game.is_game_over:
                    break
                snap = self._game.get_game_snapshot()
                state_msg = json.dumps(snapshot_to_dict(snap, self._game.game_start_time, ""))
                events, self._pending_events = self._pending_events, []
            await self._broadcast(state_msg)
            for ev in events:
                await self._broadcast(json.dumps(ev))
            await asyncio.sleep(TICK_MS / 1000)

        if self._game is not None:
            await self._send_final_state()
            await self._broadcast_rating_updates()
        log.info("Game over — loop stopped")

    async def _send_final_state(self) -> None:
        snap = self._game.get_game_snapshot()
        await self._broadcast(json.dumps(snapshot_to_dict(snap, self._game.game_start_time, self._winner_name)))
        events, self._pending_events = self._pending_events, []
        for ev in events:
            await self._broadcast(json.dumps(ev))

    # --- message routing ---

    async def _handle_message(self, raw: str, color: Color) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        if self._game is None or self._game.is_game_over:
            return
        async with self._lock:
            if msg["type"] == "move":
                self._game.request_move(Position(*msg["from"]), Position(*msg["to"]))
            elif msg["type"] == "jump":
                self._game.handle_jump(Position(*msg["cell"]))
            elif msg["type"] == "legal_moves":
                moves = self._game.get_legal_moves(Position(*msg["cell"]))
                ws = self._clients.get(color)
                if ws:
                    await ws.send(json.dumps({
                        "type": "legal_moves",
                        "cell": msg["cell"],
                        "moves": [[p.row, p.col] for p in moves],
                    }))

    # --- rating updates ---

    async def _broadcast_rating_updates(self) -> None:
        """Computes ELO deltas and sends a rating_update message to each client."""
        winner_color = next(
            (c for c, name in self._usernames.items() if name == self._winner_name), None
        )
        if winner_color is None or len(self._usernames) < 2:
            return
        loser_color  = Color.BLACK if winner_color == Color.WHITE else Color.WHITE
        w_delta, l_delta = db.update_ratings(
            self._usernames[winner_color], self._usernames[loser_color]
        )
        for color, delta in ((winner_color, w_delta), (loser_color, l_delta)):
            ws = self._clients.get(color)
            if ws:
                old = self._ratings.get(color, 1200)
                try:
                    await ws.send(json.dumps({
                        "type":       "rating_update",
                        "username":   self._usernames[color],
                        "old_rating": old,
                        "new_rating": old + delta,
                        "delta":      delta,
                    }))
                except Exception:
                    pass

    async def _broadcast(self, msg: str) -> None:
        for ws in list(self._clients.values()):
            try:
                await ws.send(msg)
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(GameServer().run())
