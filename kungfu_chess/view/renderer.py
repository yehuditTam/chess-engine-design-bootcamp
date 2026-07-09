from abc import ABC, abstractmethod
from kungfu_chess.shared.dto import BoardSnapshot


class Renderer(ABC):
    @abstractmethod
    def render(self, snapshot: BoardSnapshot) -> None:
        pass
