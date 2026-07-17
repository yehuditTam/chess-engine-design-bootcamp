from kungfu_chess.shared.constants import Color


class Player:
    def __init__(self, name: str, color: Color):
        self.name = name
        self.color = color
