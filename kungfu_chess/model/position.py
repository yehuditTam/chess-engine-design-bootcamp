from dataclasses import dataclass


# frozen=True gives free equality/hash so Position works in sets and dicts.
@dataclass(frozen=True)
class Position:
    row: int
    col: int

    def __iter__(self):
        yield self.row
        yield self.col

    def direction_to(self, other: "Position") -> tuple:
        """Returns (dr, dc) unit step toward other."""
        dr = 0 if self.row == other.row else (1 if other.row > self.row else -1)
        dc = 0 if self.col == other.col else (1 if other.col > self.col else -1)
        return dr, dc

    def __repr__(self):
        return f"({self.row}, {self.col})"
