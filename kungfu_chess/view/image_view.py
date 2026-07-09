import pygame
from kungfu_chess.view.renderer import Renderer
from kungfu_chess.shared.dto import BoardSnapshot
from kungfu_chess.shared.constants import Color, PieceType
from kungfu_chess.shared.ui_constants import TILE_SIZE

_LIGHT = (240, 217, 181)
_DARK  = (181, 136,  99)
_TEXT  = (30,  30,  30)

_SYMBOLS = {
    PieceType.KING:   "K",
    PieceType.QUEEN:  "Q",
    PieceType.ROOK:   "R",
    PieceType.BISHOP: "B",
    PieceType.KNIGHT: "N",
    PieceType.PAWN:   "P",
}


class ImageView(Renderer):
    def __init__(self, surface: pygame.Surface):
        self._surface = surface
        self._font = None

    def render(self, snapshot: BoardSnapshot) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont("segoeuisymbol", TILE_SIZE // 2, bold=True)
        for row in range(snapshot.rows):
            for col in range(snapshot.cols):
                self._draw_tile(row, col, snapshot.get(row, col))

    def _draw_tile(self, row, col, piece):
        x, y = col * TILE_SIZE, row * TILE_SIZE
        color = _LIGHT if (row + col) % 2 == 0 else _DARK
        pygame.draw.rect(self._surface, color, (x, y, TILE_SIZE, TILE_SIZE))
        if piece is None:
            return
        label = ("w" if piece.color == Color.WHITE else "b") + _SYMBOLS[piece.ptype]
        text = self._font.render(label, True, _TEXT)
        rect = text.get_rect(center=(x + TILE_SIZE // 2, y + TILE_SIZE // 2))
        self._surface.blit(text, rect)
