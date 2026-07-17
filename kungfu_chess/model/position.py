from dataclasses import dataclass

# frozen=True gives free equality and hash so Position can be used in sets/dicts
# without boilerplate.
# __iter__ allows tuple-unpacking (row, col = pos) to stay compatible with
# grid[row][col] calls.
# direction_to() lives here because it is pure coordinate math.


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
