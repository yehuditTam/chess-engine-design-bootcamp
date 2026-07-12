from dataclasses import dataclass

# Value Object: Position
# Represents a single square on the board as an immutable (row, col) pair.
# frozen=True gives free equality and hash, so Position can be used in sets and dicts.
# __iter__ allows tuple-unpacking: row, col = pos — keeps compatibility with
# existing code that passes coordinates as arguments.
# direction_to() is placed here because it is pure coordinate math with no
# knowledge of board size or piece rules.


@dataclass(frozen=True)
class Position:
    row: int
    col: int

    def __iter__(self):
        yield self.row
        yield self.col

    def direction_to(self, other: "Position") -> tuple:
        dr = 0 if self.row == other.row else (1 if other.row > self.row else -1)
        dc = 0 if self.col == other.col else (1 if other.col > self.col else -1)
        return dr, dc

    def __repr__(self):
        return f"({self.row}, {self.col})"
