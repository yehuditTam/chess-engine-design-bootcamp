from dataclasses import dataclass
from kungfu_chess.shared.constants import PieceType, Color

_VALID_TOKENS = {c.value + p.value for c in Color for p in PieceType} | {"."}


@dataclass
class ValidationError:
    code: str
    row: int = None
    token: str = None

    def __str__(self):
        parts = [f"ERROR {self.code}"]
        if self.row is not None:
            parts.append(f"row={self.row}")
        if self.token is not None:
            parts.append(f"token={self.token}")
        return " ".join(parts)


def validate_board(board_rows) -> list[ValidationError]:
    """Returns a list of errors found in the board layout, or an empty list if valid."""
    if not board_rows:
        return [ValidationError(code="EMPTY_BOARD")]
    errors = []
    width = len(board_rows[0])
    for r, row in enumerate(board_rows):
        if len(row) != width:
            errors.append(ValidationError(code="ROW_WIDTH_MISMATCH", row=r))
        for token in row:
            if token not in _VALID_TOKENS:
                errors.append(ValidationError(code="UNKNOWN_TOKEN", row=r, token=token))
    return errors
