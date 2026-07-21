"""
Run the KungFu Chess client — connects to the server and opens an OpenCV window.

Usage:
    python -m client.run_client
"""

import cv2
import time
from client.server_bridge import ServerBridge
from kungfu_chess.view.image_view import ImageView
from kungfu_chess.view.view_controller import ViewController
from kungfu_chess.view.sound_player import _play as _play_sound
from kungfu_chess.shared.ui_constants import WINDOW_TITLE, KEY_ESC
from kungfu_chess.model.position import Position

# Map bus event names → sound files
_EVENT_SOUNDS = {
    "piece_moved":    "click.mp3",
    "piece_captured": "eat.mp3",
    "piece_jumped":   "jump.mp3",
    "game_over":      "game_over.mp3",
}


class _RemoteGame:
    """
    Thin adapter that lets ViewController talk to the server
    instead of a local GameEngine.
    """

    def __init__(self, bridge: ServerBridge, local_color):
        self._bridge = bridge
        self._color = local_color
        self._snapshot = None
        self.is_game_over = False

    def update(self, snapshot, game_over):
        self._snapshot = snapshot
        self.is_game_over = game_over

    def has_piece(self, pos: Position) -> bool:
        if self._snapshot is None:
            return False
        p = self._snapshot.board.get(pos.row, pos.col)
        if p is None:
            return False
        from kungfu_chess.shared.constants import PieceState
        return p.color == self._color and p.state not in (
            PieceState.MOVING, PieceState.COOLING, PieceState.CAPTURED
        )

    def get_legal_moves(self, start: Position) -> list:
        self._bridge.request_legal_moves(start)
        return []

    def request_move(self, start: Position, end: Position):
        from kungfu_chess.shared.dto import MoveResult
        self._bridge.send_move(start, end)
        return MoveResult(ok=True)

    def handle_jump(self, cell: Position):
        self._bridge.send_jump(cell)


def _prompt_auth(bridge: ServerBridge) -> str:
    """Terminal auth loop. Returns the authenticated username."""
    while True:
        action_raw = input("(l)ogin or (r)egister? ").strip().lower()
        action = "register" if action_raw.startswith("r") else "login"
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        result = bridge.authenticate(username, password, action)
        if result["type"] == "auth_ok":
            print(f"Welcome, {result['username']}! Rating: {result['rating']}")
            # send join so server can proceed
            bridge._outgoing.put({"type": "join", "username": username})
            return username
        else:
            print(f"Auth failed: {result.get('reason', 'unknown error')}")


def main():
    bridge = ServerBridge()
    print("Connecting to server...")
    bridge.start()
    _prompt_auth(bridge)
    print(f"You are playing as: {bridge.color().name}")

    view = ImageView()
    remote_game = _RemoteGame(bridge, bridge.color())
    vc = ViewController(remote_game, view)
    winner_name = ""

    from kungfu_chess.view.image_view import _WIN_W, _WIN_H
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    init_scale = ImageView._get_scale(_WIN_W, _WIN_H)
    cv2.resizeWindow(WINDOW_TITLE, int(_WIN_W * init_scale), int(_WIN_H * init_scale))

    def on_click(event, mx, my, flags, param):
        vc.on_mouse(event, mx, my)

    cv2.setMouseCallback(WINDOW_TITLE, on_click)

    while True:
        # --- process incoming state ---
        state = bridge.poll_state()
        if state is not None:
            snap, game_over, game_start_time, w_name = state
            remote_game.update(snap, game_over)
            if game_start_time > 0 and view._start_time is None:
                view._start_time = time.time() - game_start_time
            if w_name:
                winner_name = w_name

        # --- process bus events from server ---
        for ev in bridge.poll_events():
            name = ev.get("name", "")
            if name == "game_started":
                view.start_timer()
                view.trigger_game_start_animation()
            elif name == "game_over":
                view.trigger_game_over_animation()
            sound = _EVENT_SOUNDS.get(name)
            if sound:
                _play_sound(sound)

        legal = bridge.poll_legal_moves()
        if legal is not None:
            vc.legal_moves = legal

        if remote_game._snapshot is not None:
            snap = remote_game._snapshot
            view.render(
                snap.board,
                snap.black.name, snap.white.name,
                snap.black.score, snap.white.score,
                list(snap.black.moves), list(snap.white.moves),
                list(snap.black.captured), list(snap.white.captured),
                selected=vc.selected,
                legal_moves=vc.legal_moves,
                feedback=vc.active_feedback(),
                game_over=remote_game.is_game_over,
                winner_name=winner_name,
                local_color=bridge.color().value,
            )

        key = cv2.waitKey(30)
        if key == KEY_ESC or cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
            break
        # print rating update once available after game over
        if remote_game.is_game_over:
            ru = bridge.poll_rating_update()
            if ru:
                delta_str = f"+{ru['delta']}" if ru['delta'] >= 0 else str(ru['delta'])
                print(f"{ru['username']}: {ru['new_rating']} ({delta_str})")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
