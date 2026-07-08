import sys
import time
from Game import Game
from validators import validate_board
from command_parser import parse


def parse_input(lines):
    board_rows, commands = [], []
    parsing_board = False
    for line in lines:
        line = line.strip()
        if line == "Board:":
            parsing_board = True
            continue
        if line == "Commands:":
            parsing_board = False
            continue
        if parsing_board and line:
            board_rows.append(line.split())
        elif not parsing_board and line:
            commands.append(line)
    return board_rows, commands


def main():
    board_rows, commands = parse_input(sys.stdin.read().splitlines())

    if not validate_board(board_rows):
        return

    game = Game(board_rows)

    for cmd in commands:
        if cmd.startswith("wait"):
            time.sleep(int(cmd.split()[1]) / 1000.0)
        else:
            game.handle_command(parse(cmd))

if __name__ == "__main__":
    main()
