import time
import cv2
import numpy as np
from kungfu_chess.shared.constants import JUMP_DURATION_SECONDS
from kungfu_chess.shared.ui_constants import LABEL_PAD
from kungfu_chess.view.sprite_loader import SpriteLoader

_TEXT_COLOR    = (230, 230, 230)
_ARC_BG        = (60, 60, 60)
_ARC_COOLDOWN  = (50, 220, 80)
_ARC_JUMP      = (0, 220, 255)
_ARC_THICKNESS = 5
_ARC_RADIUS    = 0.46   # fraction of tile size
_SPRITE_SCALE  = 0.92
_ANIM_STAGGER  = 0.37
_COL_LABELS    = "abcdefgh"


class BoardRenderer:
    def __init__(self, sprite_loader: SpriteLoader):
        self._loader = sprite_loader
        self._jump_start: dict[tuple, float] = {}

    def draw(self, canvas: np.ndarray, board_img: np.ndarray,
             board_x: int, board_y: int, board, tile: int, game_over: bool = False) -> None:
        """Draws the board image, all pieces, coordinate labels, and countdown arcs."""
        bh, bw = board_img.shape[:2]
        canvas[board_y:board_y + bh, board_x:board_x + bw] = board_img
        for row in range(board.rows):
            for col in range(board.cols):
                piece = board.get(row, col)
                if piece is not None:
                    self._draw_piece(canvas, piece, row, col, board_x, board_y, tile, game_over)
        self._draw_labels(canvas, board_x, board_y, tile)

    def _draw_piece(self, canvas, piece, row, col, board_x, board_y, tile, game_over) -> None:
        anim_offset = self._anim_offset(piece, row, col)
        state = "jumping" if piece.is_airborne else piece.state.value
        sprite = self._loader.load_piece_sprite(
            piece.ptype.value, piece.color.value, int(tile * _SPRITE_SCALE), state, anim_offset
        )
        sh, sw = sprite.shape[:2]
        px = board_x + col * tile + (tile - sw) // 2
        py = board_y + row * tile + (tile - sh) // 2
        self._blend(canvas, sprite, px, py)
        if not game_over:
            self._draw_countdown_arc(canvas, piece, board_x, board_y, row, col, tile)

    def _anim_offset(self, piece, row: int, col: int) -> float:
        """Returns an animation time offset — synced to jump start or staggered by position."""
        key = (row, col)
        if piece.is_airborne:
            if key not in self._jump_start:
                self._jump_start[key] = time.time()
            return -self._jump_start[key]
        self._jump_start.pop(key, None)
        return (row * 8 + col) * _ANIM_STAGGER

    def _draw_countdown_arc(self, canvas, piece, board_x, board_y, row, col, tile) -> None:
        cx = board_x + col * tile + tile // 2
        cy = board_y + row * tile + tile // 2
        r = int(tile * _ARC_RADIUS)
        if piece.is_cooling and piece.cooldown_ends_at > 0:
            total = piece.cooldown_ends_at - piece.cooldown_started_at
            remaining = piece.cooldown_ends_at - time.time()
            frac = max(0.0, min(1.0, remaining / total)) if total > 0 else 0.0
            self._draw_arc(canvas, cx, cy, r, frac, _ARC_BG, _ARC_COOLDOWN)
        elif piece.is_airborne and piece.jump_started_at > 0:
            elapsed = time.time() - piece.jump_started_at
            frac = max(0.0, min(1.0, 1.0 - elapsed / JUMP_DURATION_SECONDS))
            self._draw_arc(canvas, cx, cy, r, frac, _ARC_BG, _ARC_JUMP)

    def _draw_labels(self, canvas, board_x: int, board_y: int, tile: int) -> None:
        board_px = tile * 8
        for c, lbl in enumerate(_COL_LABELS):
            cx = board_x + c * tile + tile // 2
            self._text(canvas, lbl, cx, board_y - LABEL_PAD // 2)
            self._text(canvas, lbl, cx, board_y + board_px + LABEL_PAD // 2)
        for r in range(8):
            cy = board_y + r * tile + tile // 2
            lbl = str(8 - r)
            self._text(canvas, lbl, board_x - LABEL_PAD // 2, cy)
            self._text(canvas, lbl, board_x + board_px + LABEL_PAD // 2, cy)

    @staticmethod
    def _draw_arc(canvas, cx, cy, r, frac, bg_color, fg_color) -> None:
        """Draws a full background ring then a shrinking foreground arc from the top."""
        cv2.circle(canvas, (cx, cy), r, bg_color, _ARC_THICKNESS, cv2.LINE_AA)
        if frac > 0:
            # cv2.ellipse: 0° = right, clockwise. Start from top = -90°.
            cv2.ellipse(canvas, (cx, cy), (r, r), -90, 0, int(360 * frac),
                        fg_color, _ARC_THICKNESS, cv2.LINE_AA)

    @staticmethod
    def _blend(canvas: np.ndarray, sprite: np.ndarray, x: int, y: int) -> None:
        sh, sw = sprite.shape[:2]
        roi = canvas[y:y + sh, x:x + sw]
        if roi.shape[:2] != (sh, sw):
            return
        alpha = sprite[:, :, 3:4].astype(np.float32) / 255.0
        roi[:] = ((1 - alpha) * roi + alpha * sprite[:, :, :3]).astype(np.uint8)

    @staticmethod
    def _text(canvas: np.ndarray, txt: str, cx: int, cy: int,
              scale: float = 0.45, color=_TEXT_COLOR) -> None:
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        cv2.putText(canvas, txt, (cx - tw // 2, cy + th // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, 1, cv2.LINE_AA)
