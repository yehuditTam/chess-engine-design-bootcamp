import io
from contextlib import redirect_stdout
from kungfu_chess.io.board_parser import parse_input
from kungfu_chess.shared.validators import validate_board
from kungfu_chess.realtime.game_engine import GameEngine
from kungfu_chess.input.controller import Controller
from kungfu_chess.input.board_mapper import parse


def run_kfc(path: str) -> str:
    with open(path) as f:
        lines = f.read().splitlines()

    board_rows, commands = parse_input(lines)
    errors = validate_board(board_rows)
    if errors:
        return "\n".join(f"ERROR {e.code}" for e in errors)

    game = GameEngine(board_rows)
    controller = Controller(game, board_cols=len(board_rows[0]), board_rows=len(board_rows))
    buf = io.StringIO()
    with redirect_stdout(buf):
        for cmd in commands:
            controller.handle_command(parse(cmd))

    return buf.getvalue()
