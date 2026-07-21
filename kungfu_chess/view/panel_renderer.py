import numpy as np
import cv2
from kungfu_chess.shared.ui_constants import PANEL_PAD

_PANEL_BG     = (245, 245, 245)
_PANEL_BORDER = (180, 180, 180)
_TEXT_DARK    = (30, 30, 30)
_TEXT_LIGHT   = (230, 230, 230)
_GOLD         = (0, 180, 220)
_BAR_BLACK    = (40, 40, 40)
_BAR_WHITE    = (200, 200, 200)
_ROW_STRIPE   = (230, 230, 230)
_YOU_COLOR    = (0, 215, 255)

_BAR_H        = 52
_BAR_H_LOCAL  = 68
_MAX_MOVES    = 7
_MOVE_ROW_H   = 22
_CAP_SECTION  = 90
_CAP_ICON_SZ  = 32


class PanelRenderer:
    def __init__(self, sprite_loader=None):
        self._loader = sprite_loader

    def draw(self, canvas: np.ndarray, x: int, y: int, w: int, h: int,
             player_name: str, color_label: str, score: int,
             moves: list, captured: list = None, is_local: bool = False) -> None:
        """Draws the full side panel for one player onto the canvas."""
        panel = np.full((h, w, 3), _PANEL_BG, dtype=np.uint8)
        self._draw_header(panel, w, player_name, color_label, score, is_local)
        self._draw_move_list(panel, w, h, moves, is_local)
        self._draw_captured_section(panel, w, h, captured or [], color_label)
        canvas[y:y + h, x:x + w] = panel

    def _draw_header(self, panel, w, player_name, color_label, score, is_local) -> None:
        is_black = color_label == "Black"
        bar_color = _BAR_BLACK if is_black else _BAR_WHITE
        txt_color = _TEXT_LIGHT if is_black else _TEXT_DARK
        bar_h = _BAR_H_LOCAL if is_local else _BAR_H
        cv2.rectangle(panel, (0, 0), (w, bar_h), bar_color, -1)
        cv2.rectangle(panel, (0, 0), (w, panel.shape[0]), _PANEL_BORDER, 1)
        self._text(panel, color_label, w // 2, 22, 0.6, txt_color, bold=True)
        self._text(panel, player_name, w // 2, 42, 0.48, txt_color)
        if is_local:
            self._text(panel, ">> YOU", w // 2, 60, 0.45, _YOU_COLOR, bold=True)
            cv2.rectangle(panel, (0, 0), (w - 1, panel.shape[0] - 1), _YOU_COLOR, 3)
        score_y = 84 if is_local else 68
        divider_y = 98 if is_local else 82
        self._text(panel, f"Score: {score}", w // 2, score_y, 0.52, _GOLD, bold=True)
        cv2.line(panel, (PANEL_PAD, divider_y), (w - PANEL_PAD, divider_y), _PANEL_BORDER, 1)

    def _draw_move_list(self, panel, w, h, moves, is_local) -> None:
        header_y = 112 if is_local else 96
        self._text(panel, "Time", w // 4, header_y, 0.45, _TEXT_DARK, bold=True)
        self._text(panel, "Move", 3 * w // 4, header_y, 0.45, _TEXT_DARK, bold=True)
        cv2.line(panel, (PANEL_PAD, header_y + 14),
                 (w - PANEL_PAD, header_y + 14), _PANEL_BORDER, 1)
        cap_top = h - _CAP_SECTION
        for i, (t, m) in enumerate(moves[-_MAX_MOVES:]):
            ry = header_y + 20 + i * _MOVE_ROW_H
            if ry + _MOVE_ROW_H > cap_top:
                break
            if i % 2 == 0:
                cv2.rectangle(panel, (4, ry - 12), (w - 4, ry + 10), _ROW_STRIPE, -1)
            self._text(panel, t, w // 4, ry, 0.42, _TEXT_DARK)
            self._text(panel, m, 3 * w // 4, ry, 0.42, _TEXT_DARK)

    def _draw_captured_section(self, panel, w, h, captured, color_label) -> None:
        cap_top = h - _CAP_SECTION
        cv2.line(panel, (PANEL_PAD, cap_top), (w - PANEL_PAD, cap_top), _PANEL_BORDER, 1)
        self._text(panel, "Captured:", w // 2, cap_top + 12, 0.42, _TEXT_DARK, bold=True)
        if not captured or self._loader is None:
            return
        # Captured pieces are the opponent's color
        opponent_color = "w" if color_label == "Black" else "b"
        per_row = max(1, (w - 2 * PANEL_PAD) // (_CAP_ICON_SZ + 2))
        for i, ptype in enumerate(captured):
            col = i % per_row
            row = i // per_row
            ix = PANEL_PAD + col * (_CAP_ICON_SZ + 2)
            iy = cap_top + 18 + row * (_CAP_ICON_SZ + 2)
            if iy + _CAP_ICON_SZ > panel.shape[0]:
                break
            sprite = self._loader.load_piece_sprite(
                ptype.value, opponent_color, _CAP_ICON_SZ, "idle")
            self._blend(panel, sprite, ix, iy)

    @staticmethod
    def _blend(canvas: np.ndarray, sprite: np.ndarray, x: int, y: int) -> None:
        sh, sw = sprite.shape[:2]
        roi = canvas[y:y + sh, x:x + sw]
        if roi.shape[:2] != (sh, sw):
            return
        if sprite.shape[2] == 4:
            alpha = sprite[:, :, 3:4].astype(np.float32) / 255.0
            roi[:] = ((1 - alpha) * roi + alpha * sprite[:, :, :3]).astype(np.uint8)
        else:
            roi[:] = sprite

    @staticmethod
    def _text(canvas: np.ndarray, txt: str, cx: int, cy: int,
              scale: float = 0.55, color=_TEXT_DARK, bold: bool = False) -> None:
        thick = 2 if bold else 1
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        cv2.putText(canvas, txt, (cx - tw // 2, cy + th // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)
