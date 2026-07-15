import cv2
import numpy as np
from kungfu_chess.shared.dto import BoardSnapshot
from kungfu_chess.shared.interfaces import IRenderer
from kungfu_chess.view.sprite_loader import SpriteLoader
from kungfu_chess.view.board_renderer import BoardRenderer
from kungfu_chess.view.panel_renderer import PanelRenderer

_TILE      = 80
_BOARD_PX  = _TILE * 8
_LABEL_PAD = 24
_PANEL_W   = 220
_PANEL_PAD = 18
_TOP_BAR   = 70
_WIN_W     = _LABEL_PAD + _BOARD_PX + _LABEL_PAD + _PANEL_PAD * 2 + _PANEL_W * 2 + _PANEL_PAD * 2
_WIN_H     = _TOP_BAR + _LABEL_PAD + _BOARD_PX + _LABEL_PAD + _TOP_BAR
_BG        = (72, 72, 72)
_TEXT_LIGHT = (230, 230, 230)


class ImageView(IRenderer):
    def __init__(self, sprite_loader: SpriteLoader = None, board_renderer: BoardRenderer = None):
        self._loader         = sprite_loader or SpriteLoader()
        self._board_renderer = board_renderer or BoardRenderer(self._loader)
        self._panel_renderer = PanelRenderer()
        self._board_x = _PANEL_PAD + _PANEL_W + _PANEL_PAD + _LABEL_PAD
        self._board_y = _TOP_BAR + _LABEL_PAD

    def get_board_offset(self) -> tuple:
        return self._board_x, self._board_y, _TILE

    def render(self, board: BoardSnapshot,
               black_name="None", white_name="None",
               black_score=0,     white_score=0,
               black_moves=None,  white_moves=None,
               selected=None, feedback=None, legal_moves=None, game_over=False) -> None:

        black_moves = black_moves or []
        white_moves = white_moves or []

        canvas = np.full((_WIN_H, _WIN_W, 3), _BG, dtype=np.uint8)
        panel_h = _LABEL_PAD + _BOARD_PX + _LABEL_PAD

        self._panel_renderer.draw(canvas, _PANEL_PAD, self._board_y - _LABEL_PAD,
                                  _PANEL_W, panel_h, black_name, "Black", black_score, black_moves)
        self._panel_renderer.draw(canvas, self._board_x + _BOARD_PX + _LABEL_PAD + _PANEL_PAD,
                                  self._board_y - _LABEL_PAD,
                                  _PANEL_W, panel_h, white_name, "White", white_score, white_moves)

        board_img = self._loader.load_board_img(_BOARD_PX)
        self._board_renderer.draw(canvas, board_img, self._board_x, self._board_y, board, _TILE)

        if legal_moves:
            overlay = canvas.copy()
            for pos in legal_moves:
                x = self._board_x + pos.col * _TILE
                y = self._board_y + pos.row * _TILE
                color = (0, 60, 180) if board.get(pos.row, pos.col) else (0, 180, 60)
                cv2.rectangle(overlay, (x, y), (x + _TILE, y + _TILE), color, -1)
            cv2.addWeighted(overlay, 0.35, canvas, 0.65, 0, canvas)

        if selected is not None:
            x = self._board_x + selected.col * _TILE
            y = self._board_y + selected.row * _TILE
            cv2.rectangle(canvas, (x+2, y+2), (x+_TILE-2, y+_TILE-2), (0, 255, 0), 2)

        if feedback is not None:
            pos, color, _ = feedback
            x = self._board_x + pos.col * _TILE
            y = self._board_y + pos.row * _TILE
            cv2.rectangle(canvas, (x+2, y+2), (x+_TILE-2, y+_TILE-2), color, 3)

        if game_over:
            overlay = canvas.copy()
            cv2.rectangle(overlay, (0, 0), (_WIN_W, _WIN_H), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, canvas, 0.4, 0, canvas)
            (tw, _), _ = cv2.getTextSize("GAME OVER", cv2.FONT_HERSHEY_SIMPLEX, 2.0, 3)
            cv2.putText(canvas, "GAME OVER", (_WIN_W // 2 - tw // 2, _WIN_H // 2 - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 215, 255), 3, cv2.LINE_AA)
            (tw, _), _ = cv2.getTextSize("Press R to restart  |  ESC to exit", cv2.FONT_HERSHEY_SIMPLEX, 0.7, 1)
            cv2.putText(canvas, "Press R to restart  |  ESC to exit",
                        (_WIN_W // 2 - tw // 2, _WIN_H // 2 + 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, _TEXT_LIGHT, 1, cv2.LINE_AA)

        cv2.imshow("Kungfu Chess", canvas)
