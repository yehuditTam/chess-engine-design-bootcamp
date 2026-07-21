from kungfu_chess.shared.constants import PieceType, PieceState
from kungfu_chess.shared.interfaces import IPiece


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

    def promote(self, strategy) -> None:
        """Replace pawn strategy with queen strategy on promotion."""
        self._ptype = PieceType.QUEEN
        self.move_strategy = strategy

    def should_promote(self, row: int) -> bool:
        """True if this pawn has reached its promotion row."""
        return (
            self._ptype == PieceType.PAWN
            and hasattr(self.move_strategy, "promotion_row")
            and self.move_strategy.promotion_row == row
        )

    def requires_clear_path(self) -> bool:
        return self.move_strategy.requires_clear_path()

    def is_legal_move(self, start, end, target) -> bool:
        return self.move_strategy.is_legal(start, end, target)

    def __str__(self):
        return f"{self._color.value}{self._ptype.value}"
