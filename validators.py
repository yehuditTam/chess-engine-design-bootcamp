from constants import PieceType, Color

_VALID_TOKENS = {c.value + p.value for c in Color for p in PieceType} | {'.'}

def validate_board(board_rows):
    if not board_rows:
        return False
    width = len(board_rows[0])
    for row in board_rows:
        if len(row) != width:
            print("ERROR ROW_WIDTH_MISMATCH")
            return False
        for token in row:
            if token not in _VALID_TOKENS:
                print("ERROR UNKNOWN_TOKEN")
                return False
    return True
