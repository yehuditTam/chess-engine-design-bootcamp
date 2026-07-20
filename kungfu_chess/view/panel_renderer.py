import numpy as np
import cv2
from kungfu_chess.shared.ui_constants import PANEL_PAD

# --- colors ---
_PANEL_BG = (245, 245, 245)
_PANEL_BORDER = (180, 180, 180)
_TEXT_DARK = (30, 30, 30)
_TEXT_LIGHT = (230, 230, 230)
_GOLD = (0, 180, 220)
_BAR_BLACK = (40, 40, 40)
_BAR_WHITE = (200, 200, 200)
_ROW_STRIPE = (230, 230, 230)

# --- layout ---
_BAR_H = 52
_BAR_H_LOCAL = 68  # taller bar when "YOU" label is shown
_NAME_Y = 22
_PLAYER_Y = 42
_YOU_Y = 60
_SCORE_Y = 84
_DIVIDER_Y = 98
_HEADER_Y = 112
_MAX_MOVES = 7
_MOVE_ROW_H = 22
_CAP_SECTION = 90
_CAP_ICON_SZ = 32


class PanelRenderer:
    def __init__(self, sprite_loader=None):
        self._loader = sprite_loader

    def draw(self, canvas: np.ndarray, x: int, y: int, w: int, h: int,
             player_name: str, color_label: str, score: int, moves: list, captured: list = None,
             is_local: bool = False):
        panel = np.full((h, w, 3), _PANEL_BG, dtype=np.uint8)

        bar_color = _BAR_BLACK if color_label == "Black" else _BAR_WHITE
        txt_color = _TEXT_LIGHT if color_label == "Black" else _TEXT_DARK
        bar_h = _BAR_H_LOCAL if is_local else _BAR_H
        score_y = _SCORE_Y if is_local else _SCORE_Y - 16
        divider_y = _DIVIDER_Y if is_local else _DIVIDER_Y - 16
        header_y = _HEADER_Y if is_local else _HEADER_Y - 16
        cv2.rectangle(panel, (0, 0), (w, bar_h), bar_color, -1)
        cv2.rectangle(panel, (0, 0), (w, h), _PANEL_BORDER, 1)

        self._text(panel, color_label, w // 2, _NAME_Y, 0.6, txt_color, 2)
        self._text(panel, player_name, w // 2, _PLAYER_Y, 0.48, txt_color)

        if is_local:
            self._text(panel, ">> YOU", w // 2, _YOU_Y, 0.45, (0, 215, 255), bold=True)
            cv2.rectangle(panel, (0, 0), (w - 1, h - 1), (0, 215, 255), 3)

        self._text(panel, f"Score: {score}", w // 2, score_y, 0.52, _GOLD, 2)
        cv2.line(panel, (PANEL_PAD, divider_y), (w - PANEL_PAD, divider_y), _PANEL_BORDER, 1)

        hy = header_y
        self._text(panel, "Time", w // 4, hy, 0.45, _TEXT_DARK, 2)
        self._text(panel, "Move", 3 * w // 4, hy, 0.45, _TEXT_DARK, 2)
        cv2.line(panel, (PANEL_PAD, hy + 14), (w - PANEL_PAD, hy + 14), _PANEL_BORDER, 1)

        for i, (t, m) in enumerate(moves[-_MAX_MOVES:]):
            ry = hy + 20 + i * _MOVE_ROW_H
            if ry + _MOVE_ROW_H > h - _CAP_SECTION:
                break
            if i % 2 == 0:
                cv2.rectangle(panel, (4, ry - 12), (w - 4, ry + 10), _ROW_STRIPE, -1)
            self._text(panel, t, w // 4, ry, 0.42, _TEXT_DARK)
            self._text(panel, m, 3 * w // 4, ry, 0.42, _TEXT_DARK)

        cap_section_y = h - _CAP_SECTION
        cv2.line(
            panel, (PANEL_PAD, cap_section_y), (w - PANEL_PAD, cap_section_y), _PANEL_BORDER, 1
        )
        self._text(panel, "Captured:", w // 2, cap_section_y + 12, 0.42, _TEXT_DARK, bold=True)
        self._draw_captured_icons(panel, captured or [], w, cap_section_y + 18, color_label)

        canvas[y:y+h, x:x+w] = panel

    def _draw_captured_icons(self, panel, captured, w, top_y, color_label):
        if not captured or self._loader is None:
            return
        # Pieces shown are those captured BY this player — they are the opponent's color
        own_color = 'w' if color_label == 'Black' else 'b'
        usable_w = w - 2 * PANEL_PAD
        per_row = max(1, usable_w // (_CAP_ICON_SZ + 2))
        for i, ptype in enumerate(captured):
            row = i // per_row
            col = i % per_row
            ix = PANEL_PAD + col * (_CAP_ICON_SZ + 2)
            iy = top_y + 2 + row * (_CAP_ICON_SZ + 2)
            if iy + _CAP_ICON_SZ > panel.shape[0]:
                break
            sprite = self._loader.load_piece_sprite(ptype.value, own_color, _CAP_ICON_SZ, 'idle')
            self._blend(panel, sprite, ix, iy)

    @staticmethod
    def _blend(canvas: np.ndarray, sprite: np.ndarray, x: int, y: int):
        sh, sw = sprite.shape[:2]
        roi = canvas[y:y+sh, x:x+sw]
        if roi.shape[:2] != (sh, sw):
            return
        if sprite.shape[2] == 4:
            alpha = sprite[:, :, 3:4].astype(np.float32) / 255.0
            roi[:] = ((1 - alpha) * roi + alpha * sprite[:, :, :3]).astype(np.uint8)
        else:
            roi[:] = sprite

    @staticmethod
    def _text(canvas: np.ndarray, txt: str, cx: int, cy: int, scale=0.55, color=_TEXT_DARK,
              bold=False):
        thick = 2 if bold else 1
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        cv2.putText(canvas, txt, (cx - tw // 2, cy + th // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)
