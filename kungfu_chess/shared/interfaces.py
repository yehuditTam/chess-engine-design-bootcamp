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

    @abstractmethod
    def set_state(self, state) -> None: pass


class IBoard(ABC):
    @abstractmethod
    def get_piece(self, row, col): pass

    @abstractmethod
    def rows(self) -> int: pass

    @abstractmethod
    def cols(self) -> int: pass

    @abstractmethod
    def add_piece(self, row, col, piece): pass

    @abstractmethod
    def move_piece(self, start, end): pass

    @abstractmethod
    def remove_piece(self, row, col): pass

    @abstractmethod
    def snapshot(self): pass


class IGame(ABC):
    @abstractmethod
    def handle_command(self, cmd): pass

    @abstractmethod
    def execute_pending_moves(self): pass

    @abstractmethod
    def get_snapshot(self): pass
