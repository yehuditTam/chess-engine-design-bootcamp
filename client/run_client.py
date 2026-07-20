"""
Run the KungFu Chess client — connects to the server and opens an OpenCV window.

Usage:
    python -m client.run_client
"""

import cv2
from client.server_bridge import ServerBridge
from kungfu_chess.view.image_view import ImageView
from kungfu_chess.view.view_controller import ViewController
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
        return []  # התשובה תגיע אסינכרונית — ראה לולאה ראשית

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

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_AUTOSIZE)

    def on_click(event, mx, my, flags, param):
        vc.on_mouse(event, mx, my)

    cv2.setMouseCallback(WINDOW_TITLE, on_click)

    while True:
        state = bridge.poll_state()
        if state is not None:
            snap, game_over = state
            remote_game.update(snap, game_over)

        # עדכן תוצאת legal_moves אם הגיעה תשובה מהשרת
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
            )

        key = cv2.waitKey(30)
        if key == KEY_ESC or cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
