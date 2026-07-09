import time
from kungfu_chess.model.position import Position
from kungfu_chess.realtime.motion import PendingMove, PendingJump
from kungfu_chess.shared.constants import JUMP_DURATION_SECONDS, MOVE_DELAY_SECONDS, PieceType, PieceState


class RealTimeArbiter:
    def __init__(self, board):
        self._board = board
        self.pending_moves = []
        self.pending_jumps = []

    def is_airborne(self, cell: Position):
        return any(j.cell == cell for j in self.pending_jumps)

    def is_pending(self, cell: Position):
        return any(m.start == cell for m in self.pending_moves)

    def schedule_move(self, start: Position, end: Position):
        piece = self._board.get_piece(*start)
        if piece is not None:
            piece.set_state(PieceState.MOVING)
        self.pending_moves.append(PendingMove(start, end, time.time() + MOVE_DELAY_SECONDS))

    def schedule_jump(self, cell: Position):
        self.pending_jumps.append(PendingJump(cell, time.time() + JUMP_DURATION_SECONDS))

    def moving_colors(self):
        return {self._board.get_piece(*m.start).color for m in self.pending_moves}

    def execute_pending_moves(self):
        now = time.time()
        game_over_target = None
        for move in self.pending_moves[:]:
            if now >= move.arrive_at:
                game_over_target = self._resolve_move(move)
                if game_over_target is not None:
                    return game_over_target
        self.pending_jumps = [j for j in self.pending_jumps if now < j.land_at]
        return None

    def _resolve_move(self, move):
        moving_piece = self._board.get_piece(*move.start)
        if moving_piece is None:
            self.pending_moves.remove(move)
            return None
        target = self._board.get_piece(*move.end)
        if target is not None and target.color == moving_piece.color:
            moving_piece.set_state(PieceState.IDLE)
            self.pending_moves.remove(move)
            return None
        airborne = next((j for j in self.pending_jumps if j.cell == move.end), None)
        if airborne is not None and target is not None and target.color != moving_piece.color:
            moving_piece.set_state(PieceState.CAPTURED)
            self._board.remove_piece(*move.start)
            self.pending_moves.remove(move)
            return None
        self._board.move_piece(move.start, move.end)
        moving_piece.set_state(PieceState.IDLE)
        self.pending_moves.remove(move)
        self._check_promotion(move.end)
        if target is not None and target.ptype == PieceType.KING:
            target.set_state(PieceState.CAPTURED)
            self.pending_moves.clear()
            return target
        if target is not None:
            target.set_state(PieceState.CAPTURED)
        return None

    def _check_promotion(self, end: Position):
        piece = self._board.get_piece(*end)
        if piece is not None and piece.should_promote(end.row):
            piece.promote()
