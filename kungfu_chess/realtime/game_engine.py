from kungfu_chess.model.board import Board
from kungfu_chess.model.position import Position
from kungfu_chess.model.player import Player
from kungfu_chess.rules.rule_engine import RuleEngine
from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter
from kungfu_chess.realtime.score_tracker import ScoreTracker
from kungfu_chess.shared.constants import PieceState, Color
from kungfu_chess.shared.dto import (
    MoveResult, PieceSnapshot, BoardSnapshot, PlayerSnapshot, GameSnapshot
)
from kungfu_chess.shared.exceptions import (
    InvalidMoveError, MotionInProgressError, FriendlyFireError, CoolingError, OutOfBoundsError,
    BlockedPathError
)
from kungfu_chess.shared.interfaces import IGame
from kungfu_chess.shared.bus import EventBus, EventType


class GameEngine(IGame):
    def __init__(self, board_rows, black: Player = None, white: Player = None,
                 bus: EventBus = None):
        self._board = Board(board_rows)
        self._rule_engine = RuleEngine(self._board)
        self._arbiter = RealTimeArbiter(self._board)
        self.is_game_over = False
        black = black or Player("Player 1", Color.BLACK)
        white = white or Player("Player 2", Color.WHITE)
        self._trackers = {
            Color.BLACK: ScoreTracker(black),
            Color.WHITE: ScoreTracker(white),
        }
        self._bus = bus or EventBus()

    # --- public interface ---

    def get_snapshot(self) -> BoardSnapshot:
        grid = tuple(
            tuple(
                self._piece_snapshot(r, c)
                for c in range(self._board.cols())
            )
            for r in range(self._board.rows())
        )
        return BoardSnapshot(grid=grid, rows=self._board.rows(), cols=self._board.cols())

    def _piece_snapshot(self, r, c):
        p = self._board.get_piece(r, c)
        if p is None:
            return None
        pos = Position(r, c)
        cd = next((c for c in self._arbiter.pending_cooldowns if c.cell == pos), None)
        jmp = next((j for j in self._arbiter.pending_jumps if j.cell == pos), None)
        return PieceSnapshot(
            p.color, p.ptype,
            p.state == PieceState.COOLING,
            p.state,
            self._arbiter.is_airborne(pos),
            cd.ready_at if cd else 0.0,
            cd.started_at if cd else 0.0,
            jmp.started_at if jmp else 0.0,
        )

    def get_game_snapshot(self) -> GameSnapshot:
        board = self.get_snapshot()

        def _player_snap(color):
            t = self._trackers[color]
            return PlayerSnapshot(
                t.player.name, color, t.score, tuple(t.moves), tuple(t.captured)
            )
        return GameSnapshot(
            board=board, black=_player_snap(Color.BLACK), white=_player_snap(Color.WHITE)
        )

    def execute_pending_moves(self):
        completed, target, ends = self._arbiter.execute_pending_moves()
        game_over_pending = target is not None
        for (start, end, ptype, moving_color, captured_ptype) in completed:
            self._trackers[moving_color].record_move(ptype, start, end)
            if captured_ptype is not None and not game_over_pending:
                self._trackers[moving_color].record_capture(captured_ptype)
                self._bus.publish(
                    EventType.PIECE_CAPTURED,
                    by_color=moving_color,
                    captured_ptype=captured_ptype,
                )
            elif captured_ptype is not None:
                self._trackers[moving_color].record_capture(captured_ptype)
            self._bus.publish(
                EventType.PIECE_MOVED,
                color=moving_color,
                ptype=ptype,
                start=start,
                end=end,
            )
            if not game_over_pending:
                self._check_promotion(end)
        if target is not None:
            self.is_game_over = True
            winner = Color.WHITE if target.color == Color.BLACK else Color.BLACK
            self._bus.publish(EventType.GAME_OVER, winner_color=winner)

    def advance_time(self, milliseconds: int):
        self._arbiter.advance_time(milliseconds)

    def request_move(self, start: Position, end: Position) -> MoveResult:
        """Public move boundary. Returns MoveResult; never raises."""
        if self.is_game_over:
            return MoveResult(ok=False, reason="game_over")
        try:
            self._try_move(start, end)
            return MoveResult(ok=True)
        except CoolingError:
            return MoveResult(ok=False, reason="invalid_move")
        except MotionInProgressError:
            return MoveResult(ok=False, reason="motion_in_progress")
        except InvalidMoveError:
            return MoveResult(ok=False, reason="invalid_move")

    def handle_jump(self, cell: Position):
        if not self.is_game_over:
            piece = self._board.get_piece(*cell)
            if (piece is not None
                    and not self._arbiter.is_pending(cell)
                    and not self._arbiter.is_airborne(cell)):
                self._arbiter.schedule_jump(cell)
                self._bus.publish(
                    EventType.PIECE_JUMPED,
                    color=piece.color,
                    cell=cell,
                )

    def get_legal_moves(self, start: Position) -> list:
        piece = self._board.get_piece(*start)
        if piece is None:
            return []
        pending_starts = {m.start for m in self._arbiter.pending_moves}
        moves = []
        for r in range(self._board.rows()):
            for c in range(self._board.cols()):
                end = Position(r, c)
                try:
                    self._rule_engine.is_legal(start, end, piece, pending_starts)
                    moves.append(end)
                except (InvalidMoveError, FriendlyFireError, OutOfBoundsError, BlockedPathError):
                    pass
        return moves

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
            raise CoolingError(f"{start} is cooling down")
        target = self._board.get_piece(*end)
        piece = self._board.get_piece(*start)
        if target is not None and target.color == piece.color:
            raise FriendlyFireError(f"Friendly piece at {end}")
        pending_starts = {m.start for m in self._arbiter.pending_moves}
        moving_colors = self._arbiter.moving_colors()
        if moving_colors and piece.color not in moving_colors:
            raise MotionInProgressError(
                f"Cannot move {piece} from {start}: motion_in_progress"
            )
        if self._rule_engine.is_legal(start, end, piece, pending_starts):
            self._arbiter.schedule_move(start, end)

    # --- test helpers (never call from production code) ---

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
