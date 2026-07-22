import time
from kungfu_chess.shared.constants import Color
from kungfu_chess.realtime.motion import PendingMove, PendingJump, PendingCooldown
from kungfu_chess.shared.constants import (
    JUMP_DURATION_SECONDS, MOVE_DELAY_SECONDS, COOLDOWN_SECONDS, PieceType, PieceState
)
from kungfu_chess.model.position import Position


class RealTimeArbiter:
    """Owns all active motion objects and resolves arrivals each tick."""

    def __init__(self, board):
        self._board = board
        self.pending_moves: list[PendingMove] = []
        self.pending_jumps: list[PendingJump] = []
        self.pending_cooldowns: list[PendingCooldown] = []
        self._time_offset = 0.0

    def _now(self) -> float:
        return time.time() + self._time_offset

    def advance_time(self, milliseconds: int) -> None:
        """Shift all pending timestamps back to simulate elapsed time (used in tests)."""
        self._time_offset += milliseconds / 1000.0

    # --- state queries ---

    def is_pending(self, cell: Position) -> bool:
        return any(m.start == cell for m in self.pending_moves)

    def is_cooling(self, cell: Position) -> bool:
        return any(c.cell == cell for c in self.pending_cooldowns)

    def is_airborne(self, cell: Position) -> bool:
        return any(j.cell == cell for j in self.pending_jumps)

    def cooldown_times(self, cell: Position) -> tuple:
        """Returns (ready_at, started_at) for the cooldown at cell, or (0.0, 0.0)."""
        cd = next((c for c in self.pending_cooldowns if c.cell == cell), None)
        return (cd.ready_at, cd.started_at) if cd else (0.0, 0.0)

    def jump_started_at(self, cell: Position) -> float:
        """Returns jump started_at for the jump at cell, or 0.0."""
        j = next((j for j in self.pending_jumps if j.cell == cell), None)
        return j.started_at if j else 0.0

    def moving_color(self) -> Color | None:
        """Returns the color that currently has pieces in motion, or None."""
        for move in self.pending_moves:
            piece = self._board.get_piece(*move.start)
            if piece is not None:
                return piece.color
        return None

    # --- scheduling ---

    def schedule_move(self, start: Position, end: Position) -> None:
        """Schedules a move, computing the actual end cell after friendly-blocking."""
        piece = self._board.get_piece(*start)
        if piece is not None:
            piece.set_state(PieceState.MOVING)
        now = self._now()
        if piece is not None and piece.ptype == PieceType.KNIGHT:
            self.pending_moves.append(PendingMove(start, end, now + MOVE_DELAY_SECONDS))
            return
        actual_end = self._compute_actual_end(start, end, piece, now)
        steps = max(abs(actual_end.row - start.row), abs(actual_end.col - start.col))
        self.pending_moves.append(PendingMove(start, actual_end, now + steps * MOVE_DELAY_SECONDS))

    def schedule_jump(self, cell: Position) -> None:
        now = self._now()
        self.pending_jumps.append(PendingJump(cell, now + JUMP_DURATION_SECONDS, started_at=now))

    # --- tick ---

    def execute_pending_moves(self) -> tuple:
        """
        Resolves all moves whose arrive_at has passed.
        Returns (completed, jump_captures, game_over_target).
          completed:     list of (start, end, ptype, color, captured_ptype)
          jump_captures: list of (jumper_color, captured_ptype)
          game_over_target: the captured King piece, or None
        """
        now = self._now()
        completed, jump_captures = [], []

        for move in sorted(self.pending_moves, key=lambda m: m.arrive_at):
            if now < move.arrive_at:
                continue
            if move not in self.pending_moves:
                continue

            jump_capture = self._check_jump_capture(move)
            if jump_capture is not None:
                jump_captures.append(jump_capture)
                continue

            info, game_over_target = self._resolve_move(move)
            if info is not None:
                completed.append(info)
            if game_over_target is not None:
                self._expire_jumps(now)
                return completed, jump_captures, game_over_target

        self._expire_jumps(now)
        self._expire_cooldowns(now)
        return completed, jump_captures, None

    # --- friendly-blocking path computation ---

    def _compute_actual_end(self, start: Position, end: Position, piece, now: float) -> Position:
        """Walks the path and stops one square before a friendly destination."""
        dr, dc = start.direction_to(end)
        curr = Position(start.row + dr, start.col + dc)
        for step in range(1, max(abs(end.row - start.row), abs(end.col - start.col)) + 1):
            arrive_here = now + step * MOVE_DELAY_SECONDS
            if self._is_blocked_by_friendly(piece, curr, arrive_here, now):
                prev = Position(curr.row - dr, curr.col - dc)
                return prev if prev != start else start
            if curr == end:
                return end
            curr = Position(curr.row + dr, curr.col + dc)
        return end

    def _is_blocked_by_friendly(self, piece, cell: Position,
                                 arrive_here: float, now: float) -> bool:
        for other in self.pending_moves:
            other_piece = self._board.get_piece(*other.start)
            if other_piece is None or other_piece.color != piece.color:
                continue
            if self._will_occupy_before(other, cell, arrive_here, now):
                return True
        return False

    def _will_occupy_before(self, other: PendingMove, cell: Position,
                            arrive_here: float, now: float) -> bool:
        """True if `other` will permanently occupy `cell` before `arrive_here`."""
        if other.end != cell:
            return False
        dr, dc = other.start.direction_to(other.end)
        curr = Position(other.start.row + dr, other.start.col + dc)
        dr_steps = max(
            abs(other.end.row - other.start.row),
            abs(other.end.col - other.start.col)
        )
        for step in range(1, dr_steps + 1):
            if curr == cell and now + step * MOVE_DELAY_SECONDS <= arrive_here:
                return True
            if curr == other.end:
                return False
            curr = Position(curr.row + dr, curr.col + dc)
        return False

    # --- move resolution ---

    def _check_jump_capture(self, move: PendingMove) -> tuple | None:
        """If the moving piece lands on an airborne enemy's cell, the mover is captured."""
        moving_piece = self._board.get_piece(*move.start)
        if moving_piece is None:
            self.pending_moves.remove(move)
            return None
        target = self._board.get_piece(*move.end)
        destination_is_airborne = any(j.cell == move.end for j in self.pending_jumps)
        if destination_is_airborne and target is not None and target.color != moving_piece.color:
            moving_piece.set_state(PieceState.CAPTURED)
            self._board.remove_piece(*move.start)
            self.pending_moves.remove(move)
            return (target.color, moving_piece.ptype)
        return None

    def _resolve_move(self, move: PendingMove) -> tuple:
        """Commits the move to the board. Returns (info, game_over_target)."""
        moving_piece = self._board.get_piece(*move.start)
        if moving_piece is None:
            if move in self.pending_moves:
                self.pending_moves.remove(move)
            return None, None

        target = self._board.get_piece(*move.end)
        if target is not None and target.color == moving_piece.color:
            moving_piece.set_state(PieceState.IDLE)
            self.pending_moves.remove(move)
            return None, None

        return self._commit_move(move, moving_piece, target)

    def _commit_move(self, move: PendingMove, moving_piece, target) -> tuple:
        """Moves the piece on the board, starts cooldown, and checks for King capture."""
        captured_ptype = target.ptype if target is not None else None
        self._board.move_piece(move.start, move.end)
        moving_piece.set_state(PieceState.COOLING)
        now = self._now()
        self.pending_cooldowns.append(
            PendingCooldown(move.end, move.arrive_at + COOLDOWN_SECONDS, started_at=now)
        )
        self.pending_moves.remove(move)
        info = (move.start, move.end, moving_piece.ptype, moving_piece.color, captured_ptype)
        if target is not None:
            target.set_state(PieceState.CAPTURED)
            if target.ptype == PieceType.KING:
                self.pending_moves.clear()
                return info, target
        return info, None

    # --- expiry ---

    def _expire_jumps(self, now: float) -> None:
        self.pending_jumps = [j for j in self.pending_jumps if now < j.land_at]

    def _expire_cooldowns(self, now: float) -> None:
        for cooldown in self.pending_cooldowns:
            if now >= cooldown.ready_at:
                piece = self._board.get_piece(*cooldown.cell)
                if piece is not None and piece.state == PieceState.COOLING:
                    piece.set_state(PieceState.IDLE)
        self.pending_cooldowns = [c for c in self.pending_cooldowns if now < c.ready_at]
