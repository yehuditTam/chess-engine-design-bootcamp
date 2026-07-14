import time
from kungfu_chess.realtime.motion import PendingMove, PendingJump, PendingCooldown
from kungfu_chess.shared.constants import JUMP_DURATION_SECONDS, MOVE_DELAY_SECONDS, COOLDOWN_SECONDS, PieceType, PieceState
from kungfu_chess.model.position import Position

# RealTimeArbiter owns all timing logic.
# It is the only place that reads time.time() and compares arrival timestamps.
# _resolve_move returns the captured target instead of raising an exception so
# that GameEngine can decide what game-over means — keeping that policy decision
# out of the arbiter.
# pending_moves and pending_jumps are exposed as plain lists so tests can
# manipulate arrive_at / land_at directly without needing a fake clock.


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
        dr, dc = start.direction_to(end)
        curr = Position(start.row + dr, start.col + dc)
        step = 1
        actual_end = end
        while True:
            arrive_here = now + step * MOVE_DELAY_SECONDS
            for other in self.pending_moves:
                other_piece = self._board.get_piece(*other.start)
                if other_piece is None or other_piece.color != piece.color:
                    continue
                if self._other_occupies_at(other, curr, arrive_here, now):
                    prev = Position(curr.row - dr, curr.col - dc)
                    actual_end = prev if prev != start else start
                    break
            else:
                if curr == end:
                    break
                curr = Position(curr.row + dr, curr.col + dc)
                step += 1
                continue
            break
        steps = max(abs(actual_end.row - start.row), abs(actual_end.col - start.col))
        self.pending_moves.append(PendingMove(start, actual_end, now + steps * MOVE_DELAY_SECONDS))

    def _other_occupies_at(self, other: PendingMove, cell: Position, arrive_here: float, now: float) -> bool:
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
        return {self._board.get_piece(*m.start).color for m in self.pending_moves}

    def execute_pending_moves(self):
        now = self._now()
        arrived_ends = []
        for move in sorted(self.pending_moves, key=lambda m: m.arrive_at):
            if now >= move.arrive_at:
                game_over_target, end = self._resolve_move(move)
                if end is not None:
                    arrived_ends.append(end)
                if game_over_target is not None:
                    return game_over_target, arrived_ends
        self.pending_jumps = [j for j in self.pending_jumps if now < j.land_at]
        expired = [c for c in self.pending_cooldowns if now >= c.ready_at]
        for c in expired:
            piece = self._board.get_piece(*c.cell)
            if piece is not None and piece.state == PieceState.COOLING:
                piece.set_state(PieceState.IDLE)
        self.pending_cooldowns = [c for c in self.pending_cooldowns if now < c.ready_at]
        return None, arrived_ends

    def _resolve_move(self, move):
        moving_piece = self._board.get_piece(*move.start)
        if moving_piece is None:
            self.pending_moves.remove(move)
            return None, None
        target = self._board.get_piece(*move.end)
        if target is not None and target.color == moving_piece.color:
            moving_piece.set_state(PieceState.IDLE)
            self.pending_moves.remove(move)
            return None, None
        airborne = next((j for j in self.pending_jumps if j.cell == move.end), None)
        if airborne is not None and target is not None and target.color != moving_piece.color:
            moving_piece.set_state(PieceState.CAPTURED)
            self._board.remove_piece(*move.start)
            self.pending_moves.remove(move)
            return None, None
        self._board.move_piece(move.start, move.end)
        moving_piece.set_state(PieceState.COOLING)
        self.pending_cooldowns.append(PendingCooldown(move.end, move.arrive_at + COOLDOWN_SECONDS))
        self.pending_moves.remove(move)
        if target is not None and target.ptype == PieceType.KING:
            target.set_state(PieceState.CAPTURED)
            self.pending_moves.clear()
            return target, move.end
        if target is not None:
            target.set_state(PieceState.CAPTURED)
        return None, move.end

