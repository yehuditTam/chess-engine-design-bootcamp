import time
from dataclasses import dataclass
from typing import Tuple
from Board import Board
from commands import ClickCommand, JumpCommand, PrintBoardCommand
from constants import TILE_SIZE, MOVE_DELAY_SECONDS, JUMP_DURATION_SECONDS, PieceType
from interfaces import IGame
from exceptions import InvalidMoveError


@dataclass
class PendingMove:
    start: Tuple[int, int]
    end: Tuple[int, int]
    arrive_at: float


@dataclass
class PendingJump:
    cell: Tuple[int, int]
    land_at: float


class Game(IGame):
    def __init__(self, board_rows):
        self.board = Board(board_rows)
        self.selected = None
        self.pending_moves = []
        self.pending_jumps = []
        self.is_game_over = False

    def _is_airborne(self, cell):
        return any(j.cell == cell for j in self.pending_jumps)

    def handle_command(self, cmd):
        self.execute_pending_moves()
        if isinstance(cmd, PrintBoardCommand):
            self.board.print_board()
        elif not self.is_game_over and isinstance(cmd, JumpCommand):
            cell = (cmd.row, cmd.col)
            piece = self.board.get_piece(*cell)
            moving = any(m.start == cell for m in self.pending_moves)
            if piece is not None and not moving and not self._is_airborne(cell):
                self.pending_jumps.append(PendingJump(cell, time.time() + JUMP_DURATION_SECONDS))
            self.selected = None
        elif not self.is_game_over and isinstance(cmd, ClickCommand):
            self._handle_click(cmd.row, cmd.col)

    def _handle_click(self, row, col):
        if self.selected:
            self._try_move(self.selected, row, col)
        else:
            self._try_select(row, col)

    def _try_select(self, row, col):
        if not (0 <= row < self.board.rows() and 0 <= col < self.board.cols()):
            return
        target = self.board.get_piece(row, col)
        if target is not None and not any(m.start == (row, col) for m in self.pending_moves):
            self.selected = (row, col)

    def _try_move(self, start, row, col):
        end = (row, col)

        if any(m.start == start for m in self.pending_moves):
            self.selected = None
            return

        target = self.board.get_piece(row, col)
        piece = self.board.get_piece(*start)

        if target is not None and target.color == piece.color:
            self.selected = (row, col) if not any(m.start == end for m in self.pending_moves) else None
            return

        try:
            pending_starts = {m.start for m in self.pending_moves}
            moving_colors = {self.board.get_piece(*m.start).color for m in self.pending_moves}
            if moving_colors and piece.color not in moving_colors:
                self.selected = None
                return
            if self.board.is_legal(start, end, piece, pending_starts):
                self.pending_moves.append(PendingMove(start, end, time.time() + MOVE_DELAY_SECONDS))
        except InvalidMoveError:
            pass

        self.selected = None

    def execute_pending_moves(self):
        now = time.time()
        for move in self.pending_moves[:]:
            if now >= move.arrive_at:
                self._resolve_move(move)
                if self.is_game_over:
                    return
        self.pending_jumps = [j for j in self.pending_jumps if now < j.land_at]

    def _resolve_move(self, move):
        target = self.board.get_piece(*move.end)
        airborne_jump = next((j for j in self.pending_jumps if j.cell == move.end), None)
        moving_piece = self.board.get_piece(*move.start)
        if airborne_jump is not None and target is not None and target.color != moving_piece.color:
            self.board.remove_piece(*move.start)
            self.pending_moves.remove(move)
            return
        self.board.move_piece(move.start, move.end)
        self.pending_moves.remove(move)
        self._check_promotion(move.end)
        self._check_game_over(target)

    def _check_promotion(self, end):
        piece = self.board.get_piece(*end)
        if piece is not None and piece.ptype == PieceType.PAWN:
            promotion_row = 0 if piece.color.value == 'w' else self.board.rows() - 1
            if end[0] == promotion_row:
                piece.promote()

    def _check_game_over(self, target):
        if target is not None and target.ptype == PieceType.KING:
            self.is_game_over = True
            self.pending_moves.clear()
