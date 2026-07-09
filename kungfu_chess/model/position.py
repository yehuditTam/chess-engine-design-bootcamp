from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    row: int
    col: int

    def __iter__(self):
        yield self.row
        yield self.col

    def __repr__(self):
        return f"({self.row}, {self.col})"
