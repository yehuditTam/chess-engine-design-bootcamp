from abc import ABC, abstractmethod


class IPiece(ABC):
    @property
    @abstractmethod
    def color(self): pass

    @property
    @abstractmethod
    def ptype(self): pass

    @abstractmethod
    def requires_clear_path(self) -> bool: pass

    @abstractmethod
    def is_legal_move(self, start, end, target) -> bool: pass


class IBoard(ABC):
    @abstractmethod
    def get_piece(self, row, col): pass

    @abstractmethod
    def rows(self) -> int: pass

    @abstractmethod
    def cols(self) -> int: pass

    @abstractmethod
    def move_piece(self, start, end): pass

    @abstractmethod
    def remove_piece(self, row, col): pass

    @abstractmethod
    def is_legal(self, start, end, piece) -> bool: pass

    @abstractmethod
    def print_board(self): pass


class IGame(ABC):
    @abstractmethod
    def handle_command(self, cmd): pass

    @abstractmethod
    def execute_pending_moves(self): pass
