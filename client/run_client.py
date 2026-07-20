"""
Run the KungFu Chess client — connects to the server and opens an OpenCV window.

Usage:
    python -m client.run_client
"""

import cv2
from client.server_bridge import ServerBridge
from kungfu_chess.view.image_view import ImageView
from kungfu_chess.view.view_controller import ViewController
from kungfu_chess.view.sound_player import _play as _play_sound
from kungfu_chess.shared.ui_constants import WINDOW_TITLE, KEY_ESC
from kungfu_chess.model.position import Position


class _RemoteGame:
    """
    Thin adapter that lets ViewController talk to the server
    instead of a local GameEngine.

    ViewController expects an object with:
        has_piece(pos), get_legal_moves(pos),
        request_move(start, end), handle_jump(cell),
        is_game_over
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
        return []  # response arrives asynchronously via poll_legal_moves()

    def request_move(self, start: Position, end: Position):
        from kungfu_chess.shared.dto import MoveResult
        self._bridge.send_move(start, end)
        return MoveResult(ok=True)

    def handle_jump(self, cell: Position):
        self._bridge.send_jump(cell)


def main():
    username = input("Enter username: ").strip()
    bridge = ServerBridge()
    print("Connecting to server...")
    bridge.start(username)
    print(f"Connected. You are playing as: {bridge.color().name}")

    view = ImageView()
    remote_game = _RemoteGame(bridge, bridge.color())
    vc = ViewController(remote_game, view)
    winner_name = ""
    _prev_total_moves = 0
    _prev_total_captured = 0
    _prev_total_airborne = 0
    _prev_game_over = False

    from kungfu_chess.view.image_view import _WIN_W, _WIN_H
    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    init_scale = ImageView._get_scale(_WIN_W, _WIN_H)
    cv2.resizeWindow(WINDOW_TITLE, int(_WIN_W * init_scale), int(_WIN_H * init_scale))

    def on_click(event, mx, my, flags, param):
        vc.on_mouse(event, mx, my)

    cv2.setMouseCallback(WINDOW_TITLE, on_click)

    while True:
        state = bridge.poll_state()
        if state is not None:
            snap, game_over, game_start_time, w_name = state
            remote_game.update(snap, game_over)
            if game_start_time > 0 and view._start_time is None:
                import time
                view._start_time = time.time() - game_start_time
            if w_name:
                winner_name = w_name

            total_moves = len(snap.black.moves) + len(snap.white.moves)
            total_captured = len(snap.black.captured) + len(snap.white.captured)
            total_airborne = sum(
                1 for r in range(snap.board.rows) for c in range(snap.board.cols)
                if (p := snap.board.get(r, c)) is not None and p.is_airborne
            )
            if total_captured > _prev_total_captured:
                _play_sound("eat.mp3")
            elif total_airborne > _prev_total_airborne:
                _play_sound("jump.mp3")
            elif total_moves > _prev_total_moves:
                _play_sound("click.mp3")
            if game_over and not _prev_game_over:
                _play_sound("game_over.mp3")
            _prev_total_moves = total_moves
            _prev_total_captured = total_captured
            _prev_total_airborne = total_airborne
            _prev_game_over = game_over

        for event in bridge.poll_events():
            if event.get("type") == "sound":
                _play_sound(event.get("name", "") + ".mp3")

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

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
