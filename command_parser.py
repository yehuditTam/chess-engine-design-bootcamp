from commands import ClickCommand, JumpCommand, PrintBoardCommand, Command
from constants import TILE_SIZE


def parse(cmd: str) -> Command:
    if cmd == "print board":
        return PrintBoardCommand()
    parts = cmd.split()
    if parts[0] == "click":
        x, y = int(parts[1]), int(parts[2])
        return ClickCommand(y // TILE_SIZE, x // TILE_SIZE)
    if parts[0] == "jump":
        x, y = int(parts[1]), int(parts[2])
        return JumpCommand(y // TILE_SIZE, x // TILE_SIZE)
    raise ValueError(f"Unknown command: {cmd}")
