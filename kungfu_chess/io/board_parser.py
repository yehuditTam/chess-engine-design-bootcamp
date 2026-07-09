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
