import time
from kungfu_chess.realtime.motion import PendingMove, PendingJump, PendingCooldown
from kungfu_chess.shared.constants import (
    JUMP_DURATION_SECONDS, MOVE_DELAY_SECONDS, COOLDOWN_SECONDS, PieceType, PieceState
)
from kungfu_chess.model.position import Position


class RealTimeArbiter:
    def __init__(self, board):
        self._board = board
        self.pending_moves = []
        self.pending_jumps = []
        self.pending_cooldowns = []
        self._time_offset = 0.0

    def _now(self):
        return time.time() + self._time_offset

    def advance_time(self, milliseconds: int):
        """Shift all pending arrival timestamps back by ms, simulating elapsed time."""
        self._time_offset += milliseconds / 1000.0

    def is_cooling(self, cell: Position):
        return any(c.cell == cell for c in self.pending_cooldowns)

    def is_airborne(self, cell: Position):
        return any(j.cell == cell for j in self.pending_jumps)

    def is_pending(self, cell: Position):
        return any(m.start == cell for m in self.pending_moves)

    def schedule_move(self, start: Position, end: Position):
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

    def _compute_actual_end(self, start: Position, end: Position, piece, now: float) -> Position:
        dr, dc = start.direction_to(end)
        curr = Position(start.row + dr, start.col + dc)
        step = 1
        while True:
            arrive_here = now + step * MOVE_DELAY_SECONDS
            if self._is_cell_blocked_by_friendly(piece, curr, arrive_here, now):
                prev = Position(curr.row - dr, curr.col - dc)
                return prev if prev != start else start
            if curr == end:
                return end
            curr = Position(curr.row + dr, curr.col + dc)
            step += 1

    def _is_cell_blocked_by_friendly(
            self, piece, cell: Position, arrive_here: float, now: float
    ) -> bool:
        for other in self.pending_moves:
            other_piece = self._board.get_piece(*other.start)
            if other_piece is None or other_piece.color != piece.color:
                continue
            if self._other_occupies_at(other, cell, arrive_here, now):
                return True
        return False

    def _other_occupies_at(
            self, other: PendingMove, cell: Position, arrive_here: float, now: float
    ) -> bool:
        """Returns True if `other` will occupy `cell` by the time `arrive_here`."""
        odr, odc = other.start.direction_to(other.end)
        ocurr = Position(other.start.row + odr, other.start.col + odc)
        ostep = 1
        while True:
            o_arrive = now + ostep * MOVE_DELAY_SECONDS
            if ocurr == cell and o_arrive <= arrive_here:
                return True
            if ocurr == other.end:
                break
            ocurr = Position(ocurr.row + odr, ocurr.col + odc)
            ostep += 1
        return False

    def schedule_jump(self, cell):
        self.pending_jumps.append(PendingJump(cell, self._now() + JUMP_DURATION_SECONDS))

    def moving_colors(self):
        colors = set()
        for m in self.pending_moves:
            piece = self._board.get_piece(*m.start)
            if piece is not None:
                colors.add(piece.color)
        return colors

    def execute_pending_moves(self):
        """Returns (completed_list, game_over_target, arrived_ends).
        completed_list items: (start, end, ptype, moving_color, captured_ptype)
        """
        now = self._now()
        completed, arrived_ends = [], []
        for move in sorted(self.pending_moves, key=lambda m: m.arrive_at):
            if now < move.arrive_at:
                continue
            info, game_over_target, end = self._resolve_move_with_info(move)
            if info is not None:
                completed.append(info)
            if end is not None:
                arrived_ends.append(end)
            if game_over_target is not None:
                self._expire_jumps(now)
                return completed, game_over_target, arrived_ends
        self._expire_jumps(now)
        self._expire_cooldowns(now)
        return completed, None, arrived_ends

    def _expire_jumps(self, now: float):
        self.pending_jumps = [j for j in self.pending_jumps if now < j.land_at]

    def _expire_cooldowns(self, now: float):
        for cooldown in self.pending_cooldowns:
            if now >= cooldown.ready_at:
                piece = self._board.get_piece(*cooldown.cell)
                if piece is not None and piece.state == PieceState.COOLING:
                    piece.set_state(PieceState.IDLE)
        self.pending_cooldowns = [c for c in self.pending_cooldowns if now < c.ready_at]

    def _resolve_move_with_info(self, move):
        """Returns (info, game_over_target, end).
        info = (start, end, ptype, moving_color, captured_ptype) or None
        """
        moving_piece = self._board.get_piece(*move.start)
        if moving_piece is None:
            self.pending_moves.remove(move)
            return None, None, None

        target = self._board.get_piece(*move.end)
        if target is not None and target.color == moving_piece.color:
            moving_piece.set_state(PieceState.IDLE)
            self.pending_moves.remove(move)
            return None, None, None

        if self._moving_piece_captured_by_airborne(move, moving_piece, target):
            return None, None, None

        return self._commit_move(move, moving_piece, target)

    def _moving_piece_captured_by_airborne(self, move, moving_piece, target) -> bool:
        destination_is_airborne = any(j.cell == move.end for j in self.pending_jumps)
        if destination_is_airborne and target is not None and target.color != moving_piece.color:
            moving_piece.set_state(PieceState.CAPTURED)
            self._board.remove_piece(*move.start)
            self.pending_moves.remove(move)
            return True
        return False

    def _commit_move(self, move, moving_piece, target):
        captured_ptype = target.ptype if target is not None else None
        self._board.move_piece(move.start, move.end)
        moving_piece.set_state(PieceState.COOLING)
        self.pending_cooldowns.append(PendingCooldown(move.end, move.arrive_at + COOLDOWN_SECONDS))
        self.pending_moves.remove(move)
        info = (move.start, move.end, moving_piece.ptype, moving_piece.color, captured_ptype)
        if target is not None:
            target.set_state(PieceState.CAPTURED)
            if target.ptype == PieceType.KING:
                self.pending_moves.clear()
                return info, target, move.end
        return info, None, move.end
