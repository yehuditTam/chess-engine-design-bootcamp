import numpy as np
import cv2

_PANEL_BG     = (245, 245, 245)
_PANEL_BORDER = (180, 180, 180)
_TEXT_DARK    = (30,  30,  30)
_TEXT_LIGHT   = (230, 230, 230)
_GOLD         = (0,   180, 220)


class PanelRenderer:
    def draw(self, canvas: np.ndarray, x: int, y: int, w: int, h: int,
             player_name: str, color_label: str, score: int, moves: list):
        panel = np.full((h, w, 3), _PANEL_BG, dtype=np.uint8)

        bar_color = (40, 40, 40) if color_label == "Black" else (200, 200, 200)
        txt_color = _TEXT_LIGHT if color_label == "Black" else _TEXT_DARK
        cv2.rectangle(panel, (0, 0), (w, 52), bar_color, -1)
        cv2.rectangle(panel, (0, 0), (w, h), _PANEL_BORDER, 1)

        self._text(panel, color_label, w // 2, 22, 0.6, txt_color, 2)
        self._text(panel, player_name, w // 2, 42, 0.48, txt_color)
        self._text(panel, f"Score: {score}", w // 2, 68, 0.52, _GOLD, 2)
        cv2.line(panel, (8, 82), (w - 8, 82), _PANEL_BORDER, 1)

        hy = 96
        self._text(panel, "Time", w // 4,     hy, 0.45, _TEXT_DARK, 2)
        self._text(panel, "Move", 3 * w // 4, hy, 0.45, _TEXT_DARK, 2)
        cv2.line(panel, (8, hy + 14), (w - 8, hy + 14), _PANEL_BORDER, 1)

        row_h = 22
        for i, (t, m) in enumerate(moves[-12:]):
            ry = hy + 20 + i * row_h
            if ry + row_h > h:
                break
            if i % 2 == 0:
                cv2.rectangle(panel, (4, ry - 12), (w - 4, ry + 10), (230, 230, 230), -1)
            self._text(panel, t, w // 4,     ry, 0.42, _TEXT_DARK)
            self._text(panel, m, 3 * w // 4, ry, 0.42, _TEXT_DARK)

        canvas[y:y+h, x:x+w] = panel

    @staticmethod
    def _text(canvas: np.ndarray, txt: str, cx: int, cy: int, scale=0.55, color=_TEXT_DARK, bold=False):
        thick = 2 if bold else 1
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        cv2.putText(canvas, txt, (cx - tw // 2, cy + th // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)
