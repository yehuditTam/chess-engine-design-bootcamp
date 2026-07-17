from kungfu_chess.shared.constants import PieceType, PieceState
from kungfu_chess.shared.interfaces import IPiece

# Piece delegates movement logic to move_strategy so that adding a new piece type
# requires only a new strategy class, not changes to Piece or Board.
# State is mutated only by RealTimeArbiter so that all timing decisions stay in one place.


class Piece(IPiece):
    def __init__(self, color, ptype, move_strategy):
        self._color = color
        self._ptype = ptype
        self.state = PieceState.IDLE
        self.move_strategy = move_strategy

    @property
    def color(self):
        return self._color

    @property
    def ptype(self):
        return self._ptype

    def set_state(self, state) -> None:
        self.state = state

    def promote(self, strategy):
        self._ptype = PieceType.QUEEN
        self.move_strategy = strategy

    def should_promote(self, row):
        return (
            self._ptype == PieceType.PAWN
            and hasattr(self.move_strategy, 'promotion_row')
            and self.move_strategy.promotion_row == row
        )

    def requires_clear_path(self) -> bool:
        return self.move_strategy.requires_clear_path()

    def __str__(self):
        return f"{self.color.value}{self.ptype.value}"

    def is_legal_move(self, start, end, target):
        return self.move_strategy.is_legal(start, end, target)
