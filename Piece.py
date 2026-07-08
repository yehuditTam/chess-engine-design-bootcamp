from constants import PieceType, Color
from move_rules import KingStrategy, RookStrategy, BishopStrategy, QueenStrategy, KnightStrategy, PawnStrategy
from interfaces import IPiece

_STRATEGY_MAP = {
    PieceType.KING:   lambda color: KingStrategy(),
    PieceType.ROOK:   lambda color: RookStrategy(),
    PieceType.BISHOP: lambda color: BishopStrategy(),
    PieceType.QUEEN:  lambda color: QueenStrategy(),
    PieceType.KNIGHT: lambda color: KnightStrategy(),
    PieceType.PAWN:   lambda color: PawnStrategy(color),
}

class Piece(IPiece):
    def __init__(self, color, ptype):
        self._color = color
        self._ptype = ptype
        self.move_strategy = _STRATEGY_MAP[ptype](color)

    @property
    def color(self):
        return self._color

    @property
    def ptype(self):
        return self._ptype

    def requires_clear_path(self) -> bool:
        return self.move_strategy.requires_clear_path()

    def __str__(self):
        return f"{self.color.value}{self.ptype.value}"

    def is_legal_move(self, start, end, target):
        return self.move_strategy.is_legal(start, end, target)
