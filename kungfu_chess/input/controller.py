import sys
from kungfu_chess.model.position import Position
from kungfu_chess.input.commands import (
    ClickCommand, JumpCommand, WaitCommand, PrintBoardCommand
)
from kungfu_chess.io.board_printer import print_board
from kungfu_chess.shared.dto import MoveResult


class Controller:
    """Translates parsed commands into game actions. Owns selection state."""

    def __init__(self, game, board_cols: int, board_rows: int):
        self._game = game
        self._cols = board_cols
        self._rows = board_rows
        self.selected: Position | None = None

    def handle_click(self, pos: Position) -> None:
        """Selects a piece or moves the selected piece to the clicked cell."""
        if not self._in_bounds(pos):
            self.selected = None
            return
        if self.selected is None:
            if self._game.has_piece(pos):
                self.selected = pos
        else:
            result: MoveResult = self._game.request_move(self.selected, pos)
            if not result.ok and result.reason == "invalid_move" and self._game.has_piece(pos):
                self.selected = pos
            else:
                self.selected = None

    def handle_command(self, cmd) -> None:
        """Dispatches a typed Command to the appropriate game action."""
        self._game.execute_pending_moves()
        if isinstance(cmd, ClickCommand):
            self.handle_click(Position(cmd.row, cmd.col))
        elif isinstance(cmd, WaitCommand):
            self._game.advance_time(cmd.milliseconds)
            self._game.execute_pending_moves()
        elif isinstance(cmd, PrintBoardCommand):
            print_board(self._game.get_snapshot())
        elif isinstance(cmd, JumpCommand) and not self._game.is_game_over:
            self._game.handle_jump(Position(cmd.row, cmd.col))

    def _in_bounds(self, pos: Position) -> bool:
        return 0 <= pos.row < self._rows and 0 <= pos.col < self._cols


def main():
    from kungfu_chess.io.board_parser import TextInputParser
    from kungfu_chess.realtime.game_engine import GameEngine
    from kungfu_chess.shared.validators import validate_board
    from kungfu_chess.input.board_mapper import parse

    board_rows, commands = TextInputParser().parse(sys.stdin.read())
    errors = validate_board(board_rows)
    if errors:
        print("\n".join(f"ERROR {e.code}" for e in errors))
        return
    game = GameEngine(board_rows)
    controller = Controller(game, board_cols=len(board_rows[0]), board_rows=len(board_rows))
    for cmd in commands:
        controller.handle_command(parse(cmd))


if __name__ == "__main__":  # pragma: no cover
    main()
