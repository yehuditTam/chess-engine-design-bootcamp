class InvalidMoveError(Exception):
    pass

class OutOfBoundsError(InvalidMoveError):
    pass

class BlockedPathError(InvalidMoveError):
    pass

class FriendlyFireError(InvalidMoveError):
    pass

class MotionInProgressError(InvalidMoveError):
    """Raised when a move is requested but another move is already active.
    Reason: motion_in_progress.
    """
    reason = "motion_in_progress"
