from dataclasses import dataclass


class Command:
    pass


@dataclass
class ClickCommand(Command):
    row: int
    col: int


@dataclass
class JumpCommand(Command):
    row: int
    col: int


@dataclass
class WaitCommand(Command):
    milliseconds: int


@dataclass
class PrintBoardCommand(Command):
    pass
