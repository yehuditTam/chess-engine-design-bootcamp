import cv2
import numpy as np
import time
from kungfu_chess.shared.dto import BoardSnapshot
from kungfu_chess.shared.interfaces import IRenderer
from kungfu_chess.shared.ui_constants import (
    TILE_SIZE, BOARD_CELLS, LABEL_PAD, PANEL_W, PANEL_PAD, TOP_BAR, WINDOW_TITLE
)
from kungfu_chess.view.sprite_loader import SpriteLoader
from kungfu_chess.view.board_renderer import BoardRenderer
from kungfu_chess.view.panel_renderer import PanelRenderer

# --- window layout ---
_BOARD_PX = TILE_SIZE * BOARD_CELLS
_WIN_W = LABEL_PAD + _BOARD_PX + LABEL_PAD + PANEL_PAD * 2 + PANEL_W * 2 + PANEL_PAD * 2
_WIN_H = TOP_BAR + LABEL_PAD + _BOARD_PX + LABEL_PAD + TOP_BAR

# --- colors ---
_BG = (72, 72, 72)
_TEXT_LIGHT = (230, 230, 230)
_COLOR_SELECTED = (0, 255, 0)
_COLOR_LEGAL_CAPTURE = (0, 60, 180)
_COLOR_LEGAL_MOVE = (0, 180, 60)
_COLOR_GAME_OVER = (0, 215, 255)
_COLOR_OVERLAY = (0, 0, 0)

# --- drawing ---
_BORDER_INSET = 2
_BORDER_THIN = 2
_BORDER_THICK = 3
_LEGAL_ALPHA = 0.35
_OVERLAY_ALPHA = 0.6

# --- typography ---
_FONT_LARGE = 2.0
_FONT_MED = 0.9
_FONT_SMALL = 0.65
_FONT_THICK_LARGE = 3
_FONT_THICK_MED = 2
_FONT_THICK_SMALL = 1
_COLOR_WINNER = (0, 255, 160)
_COLOR_SUMMARY = (220, 220, 220)

# --- flash animation ---
_FLASH_START_COLOR = (0, 220, 80)    # green — game start
_FLASH_OVER_COLOR = (0, 0, 220)      # red — game over
_FLASH_START_DURATION = 0.6
_FLASH_OVER_DURATION = 0.8
_FLASH_BORDER_THICKNESS = 6


class ImageView(IRenderer):
    def __init__(self, sprite_loader: SpriteLoader = None, board_renderer: BoardRenderer = None):
        self._loader = sprite_loader or SpriteLoader()
        self._board_renderer = board_renderer or BoardRenderer(self._loader)
        self._panel_renderer = PanelRenderer(self._loader)
        self._start_time: float = None
        self._stop_time: float = None
        self._flash_until: float = 0.0
        self._flash_duration: float = 1.0
        self._flash_color: tuple = _FLASH_START_COLOR

    def _scale(self) -> float:
        try:
            rect = cv2.getWindowImageRect(WINDOW_TITLE)
            if rect[2] > 0 and rect[3] > 0:
                return min(rect[2] / _WIN_W, rect[3] / _WIN_H)
        except Exception:
            pass
        return 1.0

    @property
    def _board_x(self):
        return PANEL_PAD + PANEL_W + PANEL_PAD + LABEL_PAD

    @property
    def _board_y(self):
        return TOP_BAR + LABEL_PAD

    def start_timer(self):
        if self._start_time is None:
            self._start_time = time.time()

    def sync_timer(self, game_start_time: float) -> None:
        """Align the local timer to the server's elapsed time."""
        if self._start_time is None:
            self._start_time = time.time() - game_start_time

    def reset_timer(self):
        self._start_time = None
        self._stop_time = None
        self._flash_until = 0.0

    def trigger_game_start_animation(self):
        """Fading green border flash to signal game start."""
        self._flash_color = _FLASH_START_COLOR
        self._flash_duration = _FLASH_START_DURATION
        self._flash_until = time.time() + _FLASH_START_DURATION

    def trigger_game_over_animation(self):
        """Fading red border flash to signal game end."""
        self._flash_color = _FLASH_OVER_COLOR
        self._flash_duration = _FLASH_OVER_DURATION
        self._flash_until = time.time() + _FLASH_OVER_DURATION

    def get_board_offset(self) -> tuple:
        s = self._scale()
        return int(self._board_x * s), int(self._board_y * s), int(TILE_SIZE * s)

    def render(self, board: BoardSnapshot,
               black_name="None", white_name="None",
               black_score=0, white_score=0,
               black_moves=None, white_moves=None,
               black_captured=None, white_captured=None,
               selected=None, feedback=None, legal_moves=None,
               game_over=False, winner_name=None,
               local_color: str = None) -> None:

        canvas = np.full((_WIN_H, _WIN_W, 3), _BG, dtype=np.uint8)
        self._draw_panels(
            canvas, black_name, black_score, black_moves or [], black_captured or [],
            white_name, white_score, white_moves or [], white_captured or [],
            local_color=local_color
        )
        self._board_renderer.draw(
            canvas, self._loader.load_board_img(_BOARD_PX),
            self._board_x, self._board_y, board, TILE_SIZE, game_over
        )
        self._draw_overlays(canvas, board, selected, legal_moves, feedback)
        if game_over:
            self._draw_game_over_screen(
                canvas, winner_name or "",
                black_name, black_score, white_name, white_score
            )
        self._draw_stopwatch(canvas)
        self._draw_flash(canvas)
        cv2.imshow(WINDOW_TITLE, self._scaled(canvas))

    def _draw_overlays(self, canvas, board, selected, legal_moves, feedback) -> None:
        if legal_moves:
            self._draw_legal_moves(canvas, board, legal_moves)
        if selected is not None:
            self._draw_selection(canvas, selected)
        if feedback is not None:
            self._draw_feedback(canvas, feedback)

    def _draw_game_over_screen(self, canvas, winner_name,
                               black_name, black_score, white_name, white_score) -> None:
        if self._stop_time is None:
            self._stop_time = time.time() if self._start_time is not None else None
        elapsed = int((self._stop_time or 0) - (self._start_time or 0))
        self._draw_game_over(canvas, winner_name, black_name, black_score,
                             white_name, white_score, elapsed)

    def _scaled(self, canvas):
        s = self._scale()
        if s == 1.0:
            return canvas
        return cv2.resize(canvas, (int(_WIN_W * s), int(_WIN_H * s)),
                          interpolation=cv2.INTER_LINEAR)

    def _draw_flash(self, canvas):
        remaining = self._flash_until - time.time()
        if remaining <= 0:
            return
        alpha = remaining / self._flash_duration
        thickness = max(2, int(_FLASH_BORDER_THICKNESS * alpha))
        cv2.rectangle(canvas, (2, 2), (_WIN_W - 2, _WIN_H - 2), self._flash_color, thickness)

    def _draw_stopwatch(self, canvas):
        if self._start_time is None:
            elapsed = 0
        else:
            elapsed = int((self._stop_time or time.time()) - self._start_time)
        txt = f"{elapsed // 60:02}:{elapsed % 60:02}"
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 2)
        cv2.putText(canvas, txt,
                    (_WIN_W // 2 - tw // 2, TOP_BAR // 2 + th // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.4, _TEXT_LIGHT, 2, cv2.LINE_AA)

    def _draw_panels(self, canvas, black_name, black_score, black_moves, black_captured,
                     white_name, white_score, white_moves, white_captured,
                     local_color: str = None):
        panel_h = LABEL_PAD + _BOARD_PX + LABEL_PAD
        black_is_local = (local_color is not None and local_color.lower() in ("black", "b"))
        white_is_local = (local_color is not None and local_color.lower() in ("white", "w"))
        self._panel_renderer.draw(
            canvas, PANEL_PAD, self._board_y - LABEL_PAD,
            PANEL_W, panel_h, black_name, "Black", black_score, black_moves, black_captured,
            is_local=black_is_local
        )
        self._panel_renderer.draw(
            canvas, self._board_x + _BOARD_PX + LABEL_PAD + PANEL_PAD,
            self._board_y - LABEL_PAD,
            PANEL_W, panel_h, white_name, "White", white_score, white_moves, white_captured,
            is_local=white_is_local
        )

    def _draw_legal_moves(self, canvas, board, legal_moves):
        overlay = canvas.copy()
        for pos in legal_moves:
            x = self._board_x + pos.col * TILE_SIZE
            y = self._board_y + pos.row * TILE_SIZE
            color = _COLOR_LEGAL_CAPTURE if board.get(pos.row, pos.col) else _COLOR_LEGAL_MOVE
            cv2.rectangle(overlay, (x, y), (x + TILE_SIZE, y + TILE_SIZE), color, -1)
        cv2.addWeighted(overlay, _LEGAL_ALPHA, canvas, 1 - _LEGAL_ALPHA, 0, canvas)

    def _draw_selection(self, canvas, selected):
        x = self._board_x + selected.col * TILE_SIZE
        y = self._board_y + selected.row * TILE_SIZE
        cv2.rectangle(
            canvas,
            (x + _BORDER_INSET, y + _BORDER_INSET),
            (x + TILE_SIZE - _BORDER_INSET, y + TILE_SIZE - _BORDER_INSET),
            _COLOR_SELECTED, _BORDER_THIN
        )

    def _draw_feedback(self, canvas, feedback):
        pos, color, _ = feedback
        x = self._board_x + pos.col * TILE_SIZE
        y = self._board_y + pos.row * TILE_SIZE
        cv2.rectangle(
            canvas,
            (x + _BORDER_INSET, y + _BORDER_INSET),
            (x + TILE_SIZE - _BORDER_INSET, y + TILE_SIZE - _BORDER_INSET),
            color, _BORDER_THICK
        )

    def _draw_game_over(self, canvas, winner_name,
                        black_name, black_score, white_name, white_score, elapsed_secs):
        self._draw_dim_overlay(canvas)
        cy = _WIN_H // 2 - 90
        dur = f"{elapsed_secs // 60:02}:{elapsed_secs % 60:02}"
        scores = f"{black_name}  {black_score} pts      {white_name}  {white_score} pts"
        lines = [
            ("GAME OVER",                         _FONT_LARGE, _FONT_THICK_LARGE, _COLOR_GAME_OVER),
            (f"{winner_name} wins!",               _FONT_MED,   _FONT_THICK_MED,   _COLOR_WINNER),
            (f"Game duration:  {dur}",             _FONT_SMALL, _FONT_THICK_SMALL, _COLOR_SUMMARY),
            (scores,                              _FONT_SMALL, _FONT_THICK_SMALL, _COLOR_SUMMARY),
            ("Press R to restart  |  ESC to exit", _FONT_SMALL, _FONT_THICK_SMALL, _TEXT_LIGHT),
        ]
        gaps = [0, 70, 44, 30, 44]
        for (txt, scale, thick, color), gap in zip(lines, gaps):
            cy += gap
            self._put_centered(canvas, txt, cy, scale, thick, color)

    def _draw_dim_overlay(self, canvas) -> None:
        overlay = canvas.copy()
        cv2.rectangle(overlay, (0, 0), (_WIN_W, _WIN_H), _COLOR_OVERLAY, -1)
        cv2.addWeighted(overlay, _OVERLAY_ALPHA, canvas, 1 - _OVERLAY_ALPHA, 0, canvas)

    @staticmethod
    def _put_centered(canvas, txt, cy, scale, thick, color):
        (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
        cv2.putText(canvas, txt, (_WIN_W // 2 - tw // 2, cy + th // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)
