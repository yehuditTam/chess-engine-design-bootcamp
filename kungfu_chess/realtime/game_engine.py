import time
from kungfu_chess.model.board import Board
from kungfu_chess.model.position import Position
from kungfu_chess.rules.rule_engine import RuleEngine
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.shared.exceptions import InvalidMoveError
from kungfu_chess.shared.interfaces import IGame


class GameEngine(IGame):
    def __init__(self, board_rows):
        self._board = Board(board_rows)
        self._rule_engine = RuleEngine(self._board)
        self._arbiter = RealTimeArbiter(self._board)
        self.selected = None
        self.is_game_over = False

    # --- public interface ---

    def get_snapshot(self):
        return self._board.snapshot()

    def execute_pending_moves(self):
        target = self._arbiter.execute_pending_moves()
        if target is not None:
            self.is_game_over = True

    def handle_command(self, cmd):
        from kungfu_chess.input.commands import ClickCommand, JumpCommand, PrintBoardCommand, WaitCommand
        self.execute_pending_moves()
        if isinstance(cmd, WaitCommand):
            time.sleep(cmd.milliseconds / 1000.0)
        elif isinstance(cmd, PrintBoardCommand):
            self._print_board()
        elif not self.is_game_over and isinstance(cmd, JumpCommand):
            self._handle_jump(Position(cmd.row, cmd.col))
        elif not self.is_game_over and isinstance(cmd, ClickCommand):
            self._handle_click(Position(cmd.row, cmd.col))

    # --- private ---

    def _print_board(self):
        from kungfu_chess.io.board_printer import print_board
        print_board(self.get_snapshot())

    def _handle_jump(self, cell: Position):
        piece = self._board.get_piece(*cell)
        if piece is not None and not self._arbiter.is_pending(cell) and not self._arbiter.is_airborne(cell):
            self._arbiter.schedule_jump(cell)
        self.selected = None

    def _handle_click(self, pos: Position):
        if self.selected:
            self._try_move(self.selected, pos)
        else:
            self._try_select(pos)

    def _try_select(self, pos: Position):
        if not (0 <= pos.row < self._board.rows() and 0 <= pos.col < self._board.cols()):
            return
        target = self._board.get_piece(*pos)
        if target is not None and not self._arbiter.is_pending(pos):
            self.selected = pos

    def _try_move(self, start: Position, end: Position):
        if self._arbiter.is_pending(start):
            self.selected = None
            return
        target = self._board.get_piece(*end)
        piece = self._board.get_piece(*start)
        if target is not None and target.color == piece.color:
            self.selected = end if not self._arbiter.is_pending(end) else None
            return
        try:
            pending_starts = {m.start for m in self._arbiter.pending_moves}
            moving_colors = self._arbiter.moving_colors()
            if moving_colors and piece.color not in moving_colors:
                self.selected = None
                return
            if self._rule_engine.is_legal(start, end, piece, pending_starts):
                self._arbiter.schedule_move(start, end)
        except InvalidMoveError:
            pass
        self.selected = None

    # expose arbiter internals for tests
    @property
    def pending_moves(self):
        return self._arbiter.pending_moves

    @property
    def pending_jumps(self):
        return self._arbiter.pending_jumps

    @property
    def board(self):
        return self._board
