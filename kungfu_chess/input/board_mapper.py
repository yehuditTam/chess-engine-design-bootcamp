from kungfu_chess.input.commands import (
    ClickCommand, JumpCommand, PrintBoardCommand, WaitCommand, Command
)
from kungfu_chess.shared.ui_constants import TILE_SIZE


def parse(cmd: str) -> Command:
    """Converts a raw command string into a typed Command object."""
    if cmd == "print board":
        return PrintBoardCommand()
    parts = cmd.split()
    if parts[0] == "click":
        x, y = int(parts[1]), int(parts[2])
        return ClickCommand(y // TILE_SIZE, x // TILE_SIZE)
    if parts[0] == "jump":
        x, y = int(parts[1]), int(parts[2])
        return JumpCommand(y // TILE_SIZE, x // TILE_SIZE)
    if parts[0] == "wait":
        return WaitCommand(int(parts[1]))
    raise ValueError(f"Unknown command: {cmd}")
