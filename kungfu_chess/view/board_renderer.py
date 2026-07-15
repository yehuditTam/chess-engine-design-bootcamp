import time
import cv2
import numpy as np
from kungfu_chess.view.sprite_loader import SpriteLoader

_TEXT_LIGHT = (230, 230, 230)
_COL_LABELS = "abcdefgh"


class BoardRenderer:
    def __init__(self, sprite_loader: SpriteLoader):
        self._loader = sprite_loader
        self._jump_start: dict[tuple, float] = {}

    def draw(self, canvas: np.ndarray, board_img: np.ndarray, board_x: int, board_y: int, board, tile: int):
        bh, bw = board_img.shape[:2]
        canvas[board_y:board_y+bh, board_x:board_x+bw] = board_img

        for row in range(board.rows):
            for col in range(board.cols):
                piece = board.get(row, col)
                if piece is None:
                    continue
                key = (row, col)
                if piece.is_airborne:
                    if key not in self._jump_start:
                        self._jump_start[key] = time.time()
                    anim_offset = -self._jump_start[key]
                else:
                    self._jump_start.pop(key, None)
                    anim_offset = (row * 8 + col) * 0.37
                state = 'jumping' if piece.is_airborne else piece.state.value
                sprite = self._loader.load_piece_sprite(
                    piece.ptype.value, piece.color.value, int(tile * 0.92), state, anim_offset)
                sh, sw = sprite.shape[:2]
                px = board_x + col * tile + (tile - sw) // 2
                py = board_y + row * tile + (tile - sh) // 2
                self._blend(canvas, sprite, px, py)

        board_px = tile * 8
        label_pad = 24
        for c, lbl in enumerate(_COL_LABELS):
            cx = board_x + c * tile + tile // 2
            self._text(canvas, lbl, cx, board_y - label_pad // 2)
            self._text(canvas, lbl, cx, board_y + board_px + label_pad // 2)
        for r in range(8):
            lbl = str(8 - r)
            cy = board_y + r * tile + tile // 2
            self._text(canvas, lbl, board_x - label_pad // 2, cy)
            self._text(canvas, lbl, board_x + board_px + label_pad // 2, cy)

    @staticmethod
    def _blend(canvas: np.ndarray, sprite: np.ndarray, x: int, y: int):
        sh, sw = sprite.shape[:2]
        roi = canvas[y:y+sh, x:x+sw]
        if roi.shape[:2] != (sh, sw):
            return
        alpha = sprite[:, :, 3:4].astype(np.float32) / 255.0
        roi[:] = ((1 - alpha) * roi + alpha * sprite[:, :, :3]).astype(np.uint8)

    @staticmethod
    def _text(canvas: np.ndarray, txt: str, cx: int, cy: int, scale=0.45, color=_TEXT_LIGHT):
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        cv2.putText(canvas, txt, (cx - tw // 2, cy + th // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)
