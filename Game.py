import time
from dataclasses import dataclass
from typing import Tuple
from Board import Board
from constants import TILE_SIZE, MOVE_DELAY_SECONDS, JUMP_DURATION_SECONDS
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
        if cmd == "print board":
            self.board.print_board()
        elif not self.is_game_over and cmd.startswith("jump"):
            parts = cmd.split()
            if len(parts) == 3:
                x, y = int(parts[1]), int(parts[2])
                cell = (y // TILE_SIZE, x // TILE_SIZE)
            elif self.selected is not None:
                cell = self.selected
            else:
                cell = None
            if cell is not None:
                piece = self.board.get_piece(*cell)
                moving = any(m.start == cell for m in self.pending_moves)
                already_airborne = self._is_airborne(cell)
                if piece is not None and not moving and not already_airborne:
                    self.pending_jumps.append(PendingJump(cell, time.time() + JUMP_DURATION_SECONDS))
            self.selected = None
        elif not self.is_game_over and cmd.startswith("click"):
            parts = cmd.split()
            x, y = int(parts[1]), int(parts[2])
            row, col = y // TILE_SIZE, x // TILE_SIZE
            self._handle_click(row, col)

    def _handle_click(self, row, col):
        if self.selected:
            start = self.selected
            end = (row, col)

            if any(m.start == start for m in self.pending_moves):
                self.selected = None
                return

            target = self.board.get_piece(row, col)
            piece = self.board.get_piece(*start)

            if target is not None and target.color == piece.color:
                if not any(m.start == end for m in self.pending_moves):
                    self.selected = (row, col)
                else:
                    self.selected = None
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
        else:
            if not (0 <= row < self.board.rows() and 0 <= col < self.board.cols()):
                return
            target = self.board.get_piece(row, col)
            if target is not None and not any(m.start == (row, col) for m in self.pending_moves):
                self.selected = (row, col)

    def execute_pending_moves(self):
        from constants import PieceType
        now = time.time()
        for move in self.pending_moves[:]:
            if now >= move.arrive_at:
                target = self.board.get_piece(*move.end)
                airborne_jump = next((j for j in self.pending_jumps if j.cell == move.end), None)
                moving_piece = self.board.get_piece(*move.start)
                if airborne_jump is not None and target is not None and target.color != moving_piece.color:
                    # Airborne piece captures the arriving enemy: remove the mover, keep airborne piece
                    self.board.grid[move.start[0]][move.start[1]] = None
                    self.pending_moves.remove(move)
                    continue
                self.board.move_piece(move.start, move.end)
                self.pending_moves.remove(move)
                piece = self.board.get_piece(*move.end)
                if piece is not None and piece.ptype == PieceType.PAWN:
                    promotion_row = 0 if piece.color.value == 'w' else self.board.rows() - 1
                    if move.end[0] == promotion_row:
                        piece.promote()
                if target is not None and target.ptype == PieceType.KING:
                    self.is_game_over = True
                    self.pending_moves.clear()
                    return
        self.pending_jumps = [j for j in self.pending_jumps if now < j.land_at]
