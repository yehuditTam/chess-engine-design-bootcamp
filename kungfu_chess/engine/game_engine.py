import time
from kungfu_chess.model.board import Board
from kungfu_chess.model.position import Position
from kungfu_chess.rules.rule_engine import RuleEngine
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.shared.dto import MoveResult
from kungfu_chess.shared.exceptions import InvalidMoveError, MotionInProgressError
from kungfu_chess.shared.interfaces import IGame

# Design Pattern: Application Service
# GameEngine coordinates between Board, RuleEngine, and RealTimeArbiter.
# It owns no selection state — that belongs to Controller.
# pending_moves, pending_jumps, and board are exposed as properties so tests
# can inspect internal state without breaking encapsulation of the arbiter.


class GameEngine(IGame):
    def __init__(self, board_rows):
        self._board = Board(board_rows)
        self._rule_engine = RuleEngine(self._board)
        self._arbiter = RealTimeArbiter(self._board)
        self.is_game_over = False

    # --- public interface ---

    def get_snapshot(self):
        return self._board.snapshot()

    def execute_pending_moves(self):
        target, ends = self._arbiter.execute_pending_moves()
        for end in ends:
            self._check_promotion(end)
        if target is not None:
            self.is_game_over = True

    def advance_time(self, milliseconds: int):
        self._arbiter.advance_time(milliseconds)

    def request_move(self, start: Position, end: Position) -> MoveResult:
        """Public move boundary. Returns MoveResult; never raises."""
        if self.is_game_over:
            return MoveResult(ok=False, reason="game_over")
        try:
            self._try_move(start, end)
            return MoveResult(ok=True)
        except MotionInProgressError:
            return MoveResult(ok=False, reason="motion_in_progress")
        except InvalidMoveError:
            return MoveResult(ok=False, reason="invalid_move")

    def handle_jump(self, cell: Position):
        if not self.is_game_over:
            piece = self._board.get_piece(*cell)
            if piece is not None and not self._arbiter.is_pending(cell) and not self._arbiter.is_airborne(cell):
                self._arbiter.schedule_jump(cell)

    def has_piece(self, pos: Position) -> bool:
        """Query for Controller: is there a non-pending piece at pos?"""
        return (
            self._board.in_bounds(pos.row, pos.col)
            and self._board.get_piece(*pos) is not None
            and not self._arbiter.is_pending(pos)
            and not self._arbiter.is_cooling(pos)
        )

    # --- private ---

    def _check_promotion(self, end: Position):
        from kungfu_chess.rules.piece_rules import QueenStrategy
        piece = self._board.get_piece(*end)
        if piece is not None and piece.should_promote(end.row):
            piece.promote(QueenStrategy())

    def _try_move(self, start: Position, end: Position):
        if self._arbiter.is_pending(start):
            raise InvalidMoveError(f"{start} is already pending")
        if self._arbiter.is_cooling(start):
            raise InvalidMoveError(f"{start} is cooling down")
        target = self._board.get_piece(*end)
        piece = self._board.get_piece(*start)
        if target is not None and target.color == piece.color:
            raise InvalidMoveError(f"Friendly piece at {end}")
        pending_starts = {m.start for m in self._arbiter.pending_moves}
        moving_colors = self._arbiter.moving_colors()
        if moving_colors and piece.color not in moving_colors:
            raise MotionInProgressError(
                f"Cannot move {piece} from {start}: motion_in_progress"
            )
        if self._rule_engine.is_legal(start, end, piece, pending_starts):
            self._arbiter.schedule_move(start, end)

    # expose arbiter internals for tests
    @property
    def pending_cooldowns(self):
        return self._arbiter.pending_cooldowns

    @property
    def pending_moves(self):
        return self._arbiter.pending_moves

    @property
    def pending_jumps(self):
        return self._arbiter.pending_jumps

    @property
    def board(self):
        return self._board
