from kungfu_chess.shared.interfaces import IInputParser
import pathlib


def parse_input(lines):
    """Splits raw input lines into board rows and command strings."""
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


def load_board_csv(path: str) -> list:
    """Loads a board from a CSV file. Each cell is PieceTypeColor e.g. PW, RB."""
    safe_path = pathlib.Path(path).resolve()
    rows = []
    with open(safe_path) as f:
        for line in f:
            cells = line.strip().split(',')
            rows.append([c[1].lower() + c[0] if len(c) == 2 else '.' for c in cells])
    return rows


class TextInputParser(IInputParser):
    def parse(self, raw: str) -> tuple:
        return parse_input(raw.splitlines())
