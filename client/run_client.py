"""
Run the KungFu Chess client — connects to the server and opens an OpenCV window.

Usage:
    python -m client.run_client
"""

import cv2
from client.server_bridge import ServerBridge
from client.remote_game import RemoteGame
from client.auth import prompt_auth
from kungfu_chess.view.image_view import ImageView, _WIN_W, _WIN_H
from kungfu_chess.view.view_controller import ViewController
from kungfu_chess.view.name_dialog import get_screen_scale
from kungfu_chess.shared.ui_constants import WINDOW_TITLE, KEY_ESC


def main():
    bridge = ServerBridge()
    print("Connecting to server...")
    bridge.start()
    prompt_auth(bridge)
    print(f"You are playing as: {bridge.color().name}")

    view = ImageView()
    remote_game = RemoteGame(bridge, bridge.color())
    vc = ViewController(remote_game, view)
    winner_name = ""

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    init_scale = get_screen_scale(_WIN_W, _WIN_H)
    cv2.resizeWindow(WINDOW_TITLE, int(_WIN_W * init_scale), int(_WIN_H * init_scale))
    cv2.setMouseCallback(
        WINDOW_TITLE,
        lambda event, mx, my, flags, param: vc.on_mouse(event, mx, my)
    )

    while True:
        state = bridge.poll_state()
        if state is not None:
            snap, game_start_time, w_name = state
            remote_game.update(snap)
            if game_start_time > 0:
                view.sync_timer(game_start_time)
            if w_name:
                winner_name = w_name

        vc.handle_events(bridge.poll_events())

        legal = bridge.poll_legal_moves()
        if legal is not None:
            vc.legal_moves = legal

        if remote_game.snapshot is not None:
            snap = remote_game.snapshot
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

        if remote_game.is_game_over:
            ru = bridge.poll_rating_update()
            if ru:
                delta_str = f"+{ru['delta']}" if ru['delta'] >= 0 else str(ru['delta'])
                print(f"{ru['username']}: {ru['new_rating']} ({delta_str})")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
