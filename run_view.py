import cv2
from kungfu_chess.realtime.game_engine import GameEngine
from kungfu_chess.model.player import Player
from kungfu_chess.shared.constants import Color
from kungfu_chess.io.board_parser import load_board_csv
from kungfu_chess.view.view_controller import ViewController
from kungfu_chess.view.image_view import ImageView
from kungfu_chess.view.name_dialog import ask_player_names
from kungfu_chess.shared.ui_constants import WINDOW_TITLE, KEY_ESC


def ask_players():
    black_name, white_name = ask_player_names()
    return Player(black_name, Color.BLACK), Player(white_name, Color.WHITE)


def new_game(rows, black, white):
    return GameEngine(rows, black, white)


rows = load_board_csv('assets/board.csv')
black_player, white_player = ask_players()
game = new_game(rows, black_player, white_player)
view = ImageView()
vc = ViewController(game, view)


def on_click(event, mx, my, flags, param):
    vc.on_mouse(event, mx, my)


cv2.namedWindow(WINDOW_TITLE, cv2.WINDOW_AUTOSIZE)
game.execute_pending_moves()
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
                game_over=game.is_game_over)
    game.execute_pending_moves()
    key = cv2.waitKey(30)
    if key == KEY_ESC or cv2.getWindowProperty(WINDOW_TITLE, cv2.WND_PROP_VISIBLE) < 1:
        break
    if key == ord('r') or key == ord('R'):
        game = new_game(rows, black_player, white_player)
        vc = ViewController(game, view)
        view.reset_timer()

cv2.destroyAllWindows()
