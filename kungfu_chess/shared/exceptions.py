class InvalidMoveError(Exception):
    pass

class OutOfBoundsError(InvalidMoveError):
    pass

class BlockedPathError(InvalidMoveError):
    pass

class FriendlyFireError(InvalidMoveError):
    pass
