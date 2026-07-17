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
    """Raised when a move is requested but another move is already active."""
    reason = "motion_in_progress"


class InvalidBoardError(Exception):
    """Raised when board validation fails."""
    def __init__(self, errors):
        self.errors = errors
        super().__init__("Invalid board: " + ", ".join(str(e) for e in errors))
