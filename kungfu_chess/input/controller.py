import sys
from kungfu_chess.realtime.game_engine import GameEngine
from kungfu_chess.shared.validators import validate_board
from kungfu_chess.input.board_mapper import parse
from kungfu_chess.io.board_parser import parse_input


def main():
    board_rows, commands = parse_input(sys.stdin.read().splitlines())

    errors = validate_board(board_rows)
    if errors:
        for error in errors:
            print(error)
        return

    game = GameEngine(board_rows)

    for cmd in commands:
        game.handle_command(parse(cmd))

if __name__ == "__main__":
    main()
