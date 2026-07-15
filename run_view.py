import cv2
from kungfu_chess.realtime.game_engine import GameEngine
from kungfu_chess.io.board_parser import load_board_csv
from kungfu_chess.view.view_controller import ViewController
from kungfu_chess.view.image_view import ImageView


def new_game(rows):
    return GameEngine(rows)


rows = load_board_csv('assets/board.csv')
game = new_game(rows)
view = ImageView()
vc = ViewController(game, view)


def on_click(event, mx, my, flags, param):
    vc.on_mouse(event, mx, my)


cv2.namedWindow("Kungfu Chess", cv2.WINDOW_AUTOSIZE)
game.execute_pending_moves()
view.render(game.get_snapshot())
cv2.waitKey(1)
cv2.setMouseCallback("Kungfu Chess", on_click)

while True:
    view.render(game.get_snapshot(),
                selected=vc.selected,
                legal_moves=vc.legal_moves,
                feedback=vc.active_feedback(),
                game_over=game.is_game_over)
    game.execute_pending_moves()
    key = cv2.waitKey(30)
    if key == 27 or cv2.getWindowProperty("Kungfu Chess", cv2.WND_PROP_VISIBLE) < 1:
        break
    if key == ord('r') or key == ord('R'):
        game = new_game(rows)
        vc = ViewController(game, view)

cv2.destroyAllWindows()
