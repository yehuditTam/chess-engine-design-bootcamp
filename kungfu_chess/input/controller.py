import sys
from kungfu_chess.model.position import Position
from kungfu_chess.shared.dto import MoveResult


class Controller:
    """Translates user actions into game commands.
    Owns selection state. Never calls Board or RuleEngine directly.
    """

    def __init__(self, game, board_cols, board_rows):
        self._game = game
        self._cols = board_cols
        self._rows = board_rows
        self.selected = None

    def handle_click(self, pos: Position):
        in_bounds = 0 <= pos.row < self._rows and 0 <= pos.col < self._cols
        if self.selected is None:
            if not in_bounds:
                return
            if self._game.has_piece(pos):
                self.selected = pos
        else:
            if not in_bounds:
                self.selected = None
                return
            result: MoveResult = self._game.request_move(self.selected, pos)
            if not result.ok and result.reason == "invalid_move":
                if self._game.has_piece(pos):
                    self.selected = pos
                else:
                    self.selected = None
            else:
                self.selected = None

    def handle_command(self, cmd):
        from kungfu_chess.input.commands import (
            ClickCommand, JumpCommand, PrintBoardCommand, WaitCommand
        )
        from kungfu_chess.io.board_printer import print_board
        if isinstance(cmd, ClickCommand):
            self._game.execute_pending_moves()
            self.handle_click(Position(cmd.row, cmd.col))
        elif isinstance(cmd, WaitCommand):
            self._game.advance_time(cmd.milliseconds)
            self._game.execute_pending_moves()
        elif isinstance(cmd, PrintBoardCommand):
            self._game.execute_pending_moves()
            print_board(self._game.get_snapshot())
        elif not self._game.is_game_over and isinstance(cmd, JumpCommand):
            self._game.execute_pending_moves()
            self._game.handle_jump(Position(cmd.row, cmd.col))


def main():
    from kungfu_chess.io.board_parser import TextInputParser
    from kungfu_chess.realtime.game_engine import GameEngine
    from kungfu_chess.shared.validators import validate_board
    from kungfu_chess.input.board_mapper import parse

    parser = TextInputParser()
    board_rows, commands = parser.parse(sys.stdin.read())

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
