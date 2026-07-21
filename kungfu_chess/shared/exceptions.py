class InvalidMoveError(Exception):
    pass


class OutOfBoundsError(InvalidMoveError):
    pass


class BlockedPathError(InvalidMoveError):
    pass


class FriendlyFireError(InvalidMoveError):
    pass


class CoolingError(InvalidMoveError):
    pass


class MotionInProgressError(InvalidMoveError):
    pass


class InvalidBoardError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Invalid board: " + ", ".join(str(e) for e in errors))
