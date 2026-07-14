from enum import Enum

MOVE_DELAY_SECONDS = 1.0
JUMP_DURATION_SECONDS = 1.0
COOLDOWN_SECONDS = 2.0

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

class PieceState(Enum):
    IDLE = 'idle'
    MOVING = 'moving'
    CAPTURED = 'captured'
    COOLING = 'cooling'
