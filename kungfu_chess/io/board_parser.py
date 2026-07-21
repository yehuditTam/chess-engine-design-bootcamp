import pathlib
from kungfu_chess.shared.interfaces import IInputParser


def parse_input(lines) -> tuple:
    """Splits raw input lines into (board_rows, command_strings)."""
    board_rows, commands = [], []
    parsing_board = False
    for line in lines:
        line = line.strip()
        if line == "Board:":
            parsing_board = True
        elif line == "Commands:":
            parsing_board = False
        elif parsing_board and line:
            board_rows.append(line.split())
        elif not parsing_board and line:
            commands.append(line)
    return board_rows, commands


def load_board_csv(path: str) -> list:
    """Loads a board from a CSV file where each cell is a piece token like 'KW' or empty."""
    rows = []
    with open(pathlib.Path(path).resolve()) as f:
        for line in f:
            cells = line.strip().split(",")
            rows.append([c[1].lower() + c[0] if len(c) == 2 else "." for c in cells])
    return rows


class TextInputParser(IInputParser):
    def parse(self, raw: str) -> tuple:
        return parse_input(raw.splitlines())
