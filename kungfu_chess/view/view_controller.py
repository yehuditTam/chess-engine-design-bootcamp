import time
from kungfu_chess.model.position import Position
from kungfu_chess.shared.dto import MoveResult


class ViewController:
    """Handles mouse input from the view and owns visual selection state."""

    def __init__(self, game, view):
        self._game = game
        self._view = view
        self.selected = None
        self.legal_moves = []
        self.feedback = None

    def on_mouse(self, event, mx, my):
        import cv2
        board_x, board_y, tile = self._view.get_board_offset()
        col = (mx - board_x) // tile
        row = (my - board_y) // tile
        in_bounds = 0 <= row < 8 and 0 <= col < 8
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
            if self._game.has_piece(pos):
                self.selected = pos
                self.legal_moves = self._game.get_legal_moves(pos)
        else:
            result: MoveResult = self._game.request_move(self.selected, pos)
            if result.ok:
                self.feedback = (pos, (0, 220, 255), time.time() + 0.4)
                self.selected = None
                self.legal_moves = []
            else:
                if self._game.has_piece(pos):
                    self.selected = pos
                    self.legal_moves = self._game.get_legal_moves(pos)
                else:
                    self.feedback = (pos, (0, 0, 220), time.time() + 0.4)
                    self.selected = None
                    self.legal_moves = []

    def reset(self):
        self.selected = None
        self.legal_moves = []
        self.feedback = None

    def active_feedback(self):
        if self.feedback and time.time() < self.feedback[2]:
            return self.feedback
        return None
