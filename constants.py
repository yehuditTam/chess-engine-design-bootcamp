from enum import Enum

TILE_SIZE = 100
MOVE_DELAY_SECONDS = 1.0
JUMP_DURATION_SECONDS = 1.0

class PieceType(Enum):
    KING = 'K'
    QUEEN = 'Q'
    ROOK = 'R'
    BISHOP = 'B'
    KNIGHT = 'N'
    PAWN = 'P'

class Color(Enum):
    WHITE = 'w'
    BLACK = 'b'
