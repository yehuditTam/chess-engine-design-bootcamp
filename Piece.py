from constants import PieceType, Color
from move_rules import KingStrategy, RookStrategy, BishopStrategy, QueenStrategy, KnightStrategy, PawnStrategy
from interfaces import IPiece

_STRATEGY_MAP = {
    PieceType.KING:   lambda color, start_row, promotion_row: KingStrategy(),
    PieceType.ROOK:   lambda color, start_row, promotion_row: RookStrategy(),
    PieceType.BISHOP: lambda color, start_row, promotion_row: BishopStrategy(),
    PieceType.QUEEN:  lambda color, start_row, promotion_row: QueenStrategy(),
    PieceType.KNIGHT: lambda color, start_row, promotion_row: KnightStrategy(),
    PieceType.PAWN:   lambda color, start_row, promotion_row: PawnStrategy(color, start_row, promotion_row),
}

class Piece(IPiece):
    def __init__(self, color, ptype, start_row=None, promotion_row=None):
        self._color = color
        self._ptype = ptype
        self.move_strategy = _STRATEGY_MAP[ptype](color, start_row, promotion_row)

    @property
    def color(self):
        return self._color

    @property
    def ptype(self):
        return self._ptype

    def promote(self):
        self._ptype = PieceType.QUEEN
        self.move_strategy = QueenStrategy()

    def requires_clear_path(self) -> bool:
        return self.move_strategy.requires_clear_path()

    def __str__(self):
        return f"{self.color.value}{self.ptype.value}"

    def is_legal_move(self, start, end, target):
        return self.move_strategy.is_legal(start, end, target)
