import time as _time
from kungfu_chess.model.board import Board
from kungfu_chess.model.position import Position
from kungfu_chess.model.player import Player
from kungfu_chess.rules.rule_engine import RuleEngine
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.realtime.player_stats_tracker import PlayerStatsTracker
from kungfu_chess.shared.constants import PieceState, Color
from kungfu_chess.shared.dto import (
    MoveResult, PieceSnapshot, BoardSnapshot, PlayerSnapshot, GameSnapshot
)
from kungfu_chess.shared.exceptions import (
    InvalidMoveError, MotionInProgressError, FriendlyFireError,
    CoolingError, OutOfBoundsError, BlockedPathError
)
from kungfu_chess.shared.interfaces import IGame
from kungfu_chess.shared.bus import EventBus, EventType


class GameEngine(IGame):
    def __init__(self, board_rows, black: Player = None, white: Player = None,
                 bus: EventBus = None):
        self._board = Board(board_rows)
        self._rule_engine = RuleEngine(self._board)
        self._arbiter = RealTimeArbiter(self._board)
        self._trackers = {
            Color.BLACK: PlayerStatsTracker(black or Player("Player 1", Color.BLACK)),
            Color.WHITE: PlayerStatsTracker(white or Player("Player 2", Color.WHITE)),
        }
        self._bus = bus or EventBus()
        self._game_start_time: float = None
        self.is_game_over = False

    # --- snapshots ---

    def get_snapshot(self) -> BoardSnapshot:
        grid = tuple(
            tuple(self._piece_snapshot(r, c) for c in range(self._board.cols()))
            for r in range(self._board.rows())
        )
        return BoardSnapshot(grid=grid, rows=self._board.rows(), cols=self._board.cols())

    def get_game_snapshot(self) -> GameSnapshot:
        return GameSnapshot(
            board=self.get_snapshot(),
            black=self._player_snapshot(Color.BLACK),
            white=self._player_snapshot(Color.WHITE),
            game_over=self.is_game_over,
        )

    def _piece_snapshot(self, r: int, c: int) -> PieceSnapshot | None:
        piece = self._board.get_piece(r, c)
        if piece is None:
            return None
        pos = Position(r, c)
        state = PieceState.AIRBORNE if self._arbiter.is_airborne(pos) else piece.state
        return PieceSnapshot(
            piece.color, piece.ptype, state,
            *self._arbiter.cooldown_times(pos),
            self._arbiter.jump_started_at(pos),
        )

    def _player_snapshot(self, color: Color) -> PlayerSnapshot:
        t = self._trackers[color]
        return PlayerSnapshot(t.player.name, color, t.score, tuple(t.moves), tuple(t.captured))

    # --- public interface ---

    def execute_pending_moves(self) -> None:
        """Resolves all arrived moves and publishes resulting events."""
        completed, jump_captures, game_over_target = self._arbiter.execute_pending_moves()
        game_over_pending = game_over_target is not None

        for start, end, ptype, color, captured_ptype in completed:
            self._publish_move(start, end, ptype, color, captured_ptype, game_over_pending)

        for jumper_color, captured_ptype in jump_captures:
            self._publish_capture(jumper_color, captured_ptype)

        if game_over_pending:
            self.is_game_over = True
            winner = Color.WHITE if game_over_target.color == Color.BLACK else Color.BLACK
            self._bus.publish(EventType.GAME_OVER, winner_color=winner)

    def request_move(self, start: Position, end: Position) -> MoveResult:
        """Validates and schedules a move. Returns MoveResult; never raises."""
        if self.is_game_over:
            return MoveResult(ok=False, reason="game_over")
        try:
            self._schedule_move(start, end)
            self._ensure_started()
            return MoveResult(ok=True)
        except CoolingError:
            return MoveResult(ok=False, reason="invalid_move")
        except MotionInProgressError:
            return MoveResult(ok=False, reason="motion_in_progress")
        except (InvalidMoveError, FriendlyFireError, OutOfBoundsError, BlockedPathError):
            return MoveResult(ok=False, reason="invalid_move")

    def handle_jump(self, cell: Position) -> None:
        """Makes a piece airborne if it is idle and not already in motion."""
        if self.is_game_over:
            return
        piece = self._board.get_piece(*cell)
        if piece is None or self._arbiter.is_pending(cell) or self._arbiter.is_airborne(cell):
            return
        self._arbiter.schedule_jump(cell)
        self._ensure_started()
        self._bus.publish(EventType.PIECE_JUMPED, color=piece.color, cell=cell)

    def has_piece(self, pos: Position) -> bool:
        """True if there is an idle, selectable piece at pos."""
        return (
            self._board.in_bounds(pos.row, pos.col)
            and self._board.get_piece(*pos) is not None
            and not self._arbiter.is_pending(pos)
            and not self._arbiter.is_cooling(pos)
        )

    def get_legal_moves(self, start: Position) -> list[Position]:
        """Returns all valid destination cells for the piece at start."""
        piece = self._board.get_piece(*start)
        if piece is None:
            return []
        pending_starts = {m.start for m in self._arbiter.pending_moves}
        all_cells = [
            Position(r, c)
            for r in range(self._board.rows())
            for c in range(self._board.cols())
        ]
        return [end for end in all_cells if self._is_legal_quiet(start, end, piece, pending_starts)]

    # --- private helpers ---

    @property
    def game_start_time(self) -> float:
        """Unix timestamp of the first move/jump, or 0.0 if not yet started."""
        return self._game_start_time or 0.0

    def _ensure_started(self) -> None:
        """Fires GAME_STARTED on the first move or jump."""
        if self._game_start_time is None:
            self._game_start_time = _time.time()
            self._bus.publish(EventType.GAME_STARTED)

    def _elapsed(self) -> float:
        if self._game_start_time is None:
            return 0.0
        return _time.time() - self._game_start_time

    def _schedule_move(self, start: Position, end: Position) -> None:
        if self._arbiter.is_pending(start):
            raise InvalidMoveError(f"{start} is already pending")
        if self._arbiter.is_cooling(start):
            raise CoolingError(f"{start} is cooling down")
        piece = self._board.get_piece(*start)
        target = self._board.get_piece(*end)
        if target is not None and target.color == piece.color:
            raise FriendlyFireError(f"Friendly piece at {end}")
        moving_color = self._arbiter.moving_color()
        if moving_color is not None and piece.color != moving_color:
            raise MotionInProgressError(f"Cannot move {piece}: opponent motion in progress")
        pending_starts = {m.start for m in self._arbiter.pending_moves}
        if self._rule_engine.is_legal(start, end, piece, pending_starts):
            self._arbiter.schedule_move(start, end)

    def _publish_move(self, start, end, ptype, color, captured_ptype, game_over_pending) -> None:
        elapsed = self._elapsed()
        time_str, move_str = self._trackers[color].record_move(ptype, start, end, elapsed)
        self._bus.publish(EventType.MOVE_LOGGED, color=color, time_str=time_str, move_str=move_str)
        if captured_ptype is not None and not game_over_pending:
            self._publish_capture(color, captured_ptype)
        self._bus.publish(EventType.PIECE_MOVED, color=color, ptype=ptype, start=start, end=end)
        if not game_over_pending:
            self._check_promotion(end)

    def _publish_capture(self, color: Color, captured_ptype) -> None:
        new_score = self._trackers[color].record_capture(captured_ptype)
        self._bus.publish(EventType.PIECE_CAPTURED, by_color=color, captured_ptype=captured_ptype)
        self._bus.publish(EventType.SCORE_UPDATED, color=color, score=new_score,
                          captured_ptype=captured_ptype)

    def _check_promotion(self, end: Position) -> None:
        from kungfu_chess.rules.piece_rules import QueenStrategy  # avoid circular import
        piece = self._board.get_piece(*end)
        if piece is not None and piece.should_promote(end.row):
            piece.promote(QueenStrategy())

    def _is_legal_quiet(self, start, end, piece, pending_starts) -> bool:
        """Returns True if the move is legal, False instead of raising."""
        try:
            return self._rule_engine.is_legal(start, end, piece, pending_starts)
        except (InvalidMoveError, FriendlyFireError, OutOfBoundsError, BlockedPathError):
            return False

    # --- test helpers ---

    def advance_time(self, milliseconds: int) -> None:
        self._arbiter.advance_time(milliseconds)

    def _expire_pending_moves(self):
        for m in self._arbiter.pending_moves:
            m.arrive_at = self._arbiter._now() - 1

    def _expire_pending_cooldowns(self):
        for c in self._arbiter.pending_cooldowns:
            c.ready_at = self._arbiter._now() - 1

    def _expire_pending_jumps(self):
        for j in self._arbiter.pending_jumps:
            j.land_at = self._arbiter._now() - 1

    @property
    def pending_moves(self):
        return self._arbiter.pending_moves

    @property
    def pending_jumps(self):
        return self._arbiter.pending_jumps

    @property
    def pending_cooldowns(self):
        return self._arbiter.pending_cooldowns

    @property
    def board(self):
        return self._board
