import cv2
from kungfu_chess.realtime.game_engine import GameEngine
from kungfu_chess.model.player import Player
from kungfu_chess.shared.constants import Color
from kungfu_chess.io.board_parser import load_board_csv
from kungfu_chess.view.view_controller import ViewController
from kungfu_chess.view.image_view import ImageView, _WIN_W, _WIN_H
from kungfu_chess.view.name_dialog import ask_player_names
from kungfu_chess.view.sound_player import init_sounds
from kungfu_chess.shared.bus import EventBus, EventType
from kungfu_chess.shared.ui_constants import WINDOW_TITLE, KEY_ESC


def ask_players():
    black_name, white_name = ask_player_names()
    return Player(black_name, Color.BLACK), Player(white_name, Color.WHITE)


rows = load_board_csv('assets/board.csv')
black_player, white_player = ask_players()
view = ImageView()


class _State:
    winner_name = None


def _subscribe(bus: EventBus, game: GameEngine):
    """Register all bus subscribers for one game session."""
    init_sounds(bus)
    bus.subscribe(
        EventType.GAME_OVER,
        lambda winner_color, **_: setattr(
            _State, 'winner_name',
            black_player.name if winner_color.value == 'b' else white_player.name
        )
    )
    bus.subscribe(EventType.GAME_STARTED, lambda **_: view.trigger_game_start_animation())
    bus.subscribe(EventType.GAME_OVER, lambda **_: view.trigger_game_over_animation())
    # Timer starts on first move or jump (GAME_STARTED fires from engine)
    bus.subscribe(EventType.GAME_STARTED, lambda **_: view.start_timer())


def new_game():
    # Create a fresh bus each restart — avoids subscription accumulation
    bus = EventBus()
    game = GameEngine(rows, black_player, white_player, bus=bus)
    _subscribe(bus, game)
    return game


game = new_game()
vc = ViewController(game, view)


def on_click(event, mx, my, flags, param):
    vc.on_mouse(event, mx, my)


cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_NORMAL)
game.execute_pending_moves()
_init_scale = ImageView._get_scale(_WIN_W, _WIN_H)
cv2.resizeWindow(WINDOW_TITLE, int(_WIN_W * _init_scale), int(_WIN_H * _init_scale))
snap = game.get_game_snapshot()
view.render(snap.board, snap.black.name, snap.white.name, snap.black.score, snap.white.score,
            list(snap.black.moves), list(snap.white.moves),
            list(snap.black.captured), list(snap.white.captured))
cv2.waitKey(1)
cv2.setMouseCallback(WINDOW_TITLE, on_click)

while True:
    snap = game.get_game_snapshot()
    view.render(snap.board,
                snap.black.name, snap.white.name,
                snap.black.score, snap.white.score,
                list(snap.black.moves), list(snap.white.moves),
                list(snap.black.captured), list(snap.white.captured),
                selected=vc.selected,
                legal_moves=vc.legal_moves,
                feedback=vc.active_feedback(),
                game_over=game.is_game_over,
                winner_name=_State.winner_name)
    game.execute_pending_moves()
    key = cv2.waitKey(30)
    if key == KEY_ESC or cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
        break
    if key == ord('r') or key == ord('R'):
        game = new_game()
        vc = ViewController(game, view)
        _State.winner_name = None
        view.reset_timer()

cv2.destroyAllWindows()
