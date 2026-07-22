from kungfu_chess.model.position import Position
from kungfu_chess.shared.constants import PieceState
from kungfu_chess.shared.dto import MoveResult
from kungfu_chess.shared.interfaces import IGame


class RemoteGame(IGame):

    def __init__(self, bridge, local_color):
        self._bridge = bridge
        self._color = local_color
        self._snapshot = None

    def update(self, snapshot) -> None:
        self._snapshot = snapshot

    @property
    def snapshot(self):
        return self._snapshot

    @property
    def is_game_over(self) -> bool:
        return self._snapshot is not None and self._snapshot.game_over

    def has_piece(self, pos: Position) -> bool:
        if self._snapshot is None:
            return False
        p = self._snapshot.board.get(pos.row, pos.col)
        if p is None:
            return False
        return p.color == self._color and p.state not in (
            PieceState.MOVING, PieceState.COOLING, PieceState.CAPTURED
        )

    def get_legal_moves(self, start: Position) -> list:
        self._bridge.request_legal_moves(start)
        return []

    def request_move(self, start: Position, end: Position) -> MoveResult:
        self._bridge.send_move(start, end)
        return MoveResult(ok=True)

    def handle_jump(self, cell: Position) -> None:
        self._bridge.send_jump(cell)

    def execute_pending_moves(self) -> None:
        pass

    def get_snapshot(self):
        return self._snapshot.board if self._snapshot else None

    def advance_time(self, milliseconds: int) -> None:
        pass
