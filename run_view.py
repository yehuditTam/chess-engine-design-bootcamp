import cv2
from kungfu_chess.realtime.game_engine import GameEngine
from kungfu_chess.model.player import Player
from kungfu_chess.shared.constants import Color
from kungfu_chess.io.board_parser import load_board_csv
from kungfu_chess.view.view_controller import ViewController
from kungfu_chess.view.image_view import ImageView, _WIN_W, _WIN_H
from kungfu_chess.view.name_dialog import ask_player_names, get_screen_scale
from kungfu_chess.view.sound_player import init_sounds
from kungfu_chess.shared.bus import EventBus, EventType
from kungfu_chess.shared.ui_constants import WINDOW_TITLE, KEY_ESC

_BOARD_CSV = "assets/board.csv"


class _Session:
    """Holds mutable per-game state that bus callbacks need to write into."""
    def __init__(self):
        self.winner_name = ""


def _new_game(rows, black: Player, white: Player, view: ImageView) -> tuple:
    """Creates a fresh GameEngine with all bus subscriptions wired. Returns (game, vc, session)."""
    bus     = EventBus()
    session = _Session()
    game    = GameEngine(rows, black, white, bus=bus)
    init_sounds(bus)
    bus.subscribe(EventType.GAME_STARTED, lambda **_: view.start_timer())
    bus.subscribe(EventType.GAME_STARTED, lambda **_: view.trigger_game_start_animation())
    bus.subscribe(EventType.GAME_OVER,    lambda **_: view.trigger_game_over_animation())
    bus.subscribe(
        EventType.GAME_OVER,
        lambda winner_color, **_: setattr(
            session, "winner_name",
            black.name if winner_color == Color.BLACK else white.name
        ),
    )
    vc = ViewController(game, view)
    return game, vc, session


def main():
    black_name, white_name = ask_player_names()
    black = Player(black_name, Color.BLACK)
    white = Player(white_name, Color.WHITE)
    rows  = load_board_csv(_BOARD_CSV)
    view  = ImageView()

    cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
    scale = get_screen_scale(_WIN_W, _WIN_H)
    cv2.resizeWindow(WINDOW_TITLE, int(_WIN_W * scale), int(_WIN_H * scale))

    game, vc, session = _new_game(rows, black, white, view)

    def on_click(event, mx, my, flags, param):
        vc.on_mouse(event, mx, my)

    cv2.setMouseCallback(WINDOW_TITLE, on_click)

    while True:
        game.execute_pending_moves()
        snap = game.get_game_snapshot()
        view.render(
            snap.board,
            snap.black.name, snap.white.name,
            snap.black.score, snap.white.score,
            list(snap.black.moves), list(snap.white.moves),
            list(snap.black.captured), list(snap.white.captured),
            selected=vc.selected,
            legal_moves=vc.legal_moves,
            feedback=vc.active_feedback(),
            game_over=game.is_game_over,
            winner_name=session.winner_name,
        )
        key = cv2.waitKey(30)
        if key == KEY_ESC or cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
            break
        if key in (ord("r"), ord("R")):
            game, vc, session = _new_game(rows, black, white, view)
            cv2.setMouseCallback(WINDOW_TITLE, lambda e, mx, my, f, p: vc.on_mouse(e, mx, my))
            view.reset_timer()

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
