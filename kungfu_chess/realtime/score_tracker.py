import time
from kungfu_chess.model.player import Player
from kungfu_chess.shared.constants import PieceType

_PIECE_VALUE = {
    PieceType.PAWN:   1,
    PieceType.BISHOP: 3,
    PieceType.KNIGHT: 3,
    PieceType.ROOK:   5,
    PieceType.QUEEN:  9,
    PieceType.KING:   0,
}

_COL_LETTERS = "abcdefgh"


def _cell_name(pos) -> str:
    return f"{_COL_LETTERS[pos.col]}{8 - pos.row}"


class ScoreTracker:
    def __init__(self, player: Player):
        self.player = player
        self._score = 0
        self._moves: list = []
        self._captured: list = []
        self._start_time = time.time()

    @property
    def score(self) -> int:
        return self._score

    @property
    def moves(self) -> list:
        return list(self._moves)

    def record_move(self, ptype: PieceType, start, end) -> None:
        elapsed = int(time.time() - self._start_time)
        t = f"{elapsed // 60:02}:{elapsed % 60:02}"
        move_str = f"{ptype.value} {_cell_name(start)}->{_cell_name(end)}"
        self._moves.append((t, move_str))

    def record_capture(self, captured_ptype: PieceType) -> None:
        self._score += _PIECE_VALUE[captured_ptype]
        self._captured.append(captured_ptype)

    @property
    def captured(self) -> list:
        return list(self._captured)
