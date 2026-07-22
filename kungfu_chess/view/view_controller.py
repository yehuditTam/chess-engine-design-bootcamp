import time
import cv2
from kungfu_chess.model.position import Position
from kungfu_chess.shared.dto import MoveResult
from kungfu_chess.shared.ui_constants import FEEDBACK_TTL, BOARD_CELLS
from kungfu_chess.view.sound_player import play_error, _play as _play_sound

_COLOR_OK      = (0, 220, 255)
_COLOR_ERR     = (0, 0, 220)
_COLOR_BLOCKED = (0, 140, 255)

_EVENT_SOUNDS = {
    "piece_moved":    "click.mp3",
    "piece_captured": "eat.mp3",
    "piece_jumped":   "jump.mp3",
    "game_over":      "game_over.mp3",
}


class ViewController:
    """Handles mouse input and owns visual selection state."""

    def __init__(self, game, view):
        self._game = game
        self._view = view
        self.selected: Position | None = None
        self.legal_moves: list = []
        self.feedback: tuple | None = None

    def handle_events(self, events: list[dict]) -> None:
        """Processes server events — triggers animations and plays sounds."""
        for ev in events:
            name = ev.get("name", "")
            if name == "game_started":
                self._view.start_timer()
                self._view.trigger_game_start_animation()
            elif name == "game_over":
                self._view.trigger_game_over_animation()
            sound = _EVENT_SOUNDS.get(name)
            if sound:
                _play_sound(sound)

    def on_mouse(self, event, mx: int, my: int) -> None:
        board_x, board_y, tile = self._view.get_board_offset()
        col = (mx - board_x) // tile
        row = (my - board_y) // tile
        in_bounds = 0 <= row < BOARD_CELLS and 0 <= col < BOARD_CELLS
        pos = Position(row, col) if in_bounds else None

        if event == cv2.EVENT_RBUTTONDOWN:
            if pos:
                self._game.handle_jump(pos)
            return

        if event != cv2.EVENT_LBUTTONDOWN:
            return

        if not in_bounds:
            self.selected = None
            self.legal_moves = []
            return

        if self.selected is None:
            self._try_select(pos)
        else:
            self._try_move(pos)

    def active_feedback(self) -> tuple | None:
        """Returns the current feedback tuple if still within TTL, else None."""
        if self.feedback and time.time() < self.feedback[2]:
            return self.feedback
        return None

    def reset(self) -> None:
        self.selected = None
        self.legal_moves = []
        self.feedback = None

    def _try_select(self, pos: Position) -> None:
        if self._game.has_piece(pos):
            self.selected = pos
            self.legal_moves = self._game.get_legal_moves(pos)

    def _try_move(self, pos: Position) -> None:
        result: MoveResult = self._game.request_move(self.selected, pos)
        if result.ok:
            self.feedback = (pos, _COLOR_OK, time.time() + FEEDBACK_TTL)
            self.selected = None
            self.legal_moves = []
        elif self._game.has_piece(pos):
            self.selected = pos
            self.legal_moves = self._game.get_legal_moves(pos)
        else:
            color = _COLOR_BLOCKED if result.reason == "motion_in_progress" else _COLOR_ERR
            self.feedback = (pos, color, time.time() + FEEDBACK_TTL)
            self.selected = None
            self.legal_moves = []
            play_error()
