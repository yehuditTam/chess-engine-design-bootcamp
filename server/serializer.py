from kungfu_chess.shared.dto import GameSnapshot, BoardSnapshot, PlayerSnapshot, PieceSnapshot
from kungfu_chess.shared.constants import Color, PieceType, PieceState


def snapshot_to_dict(snap: GameSnapshot,
                     game_start_time: float = 0.0, winner_name: str = "") -> dict:
    """Converts a GameSnapshot to a JSON-serialisable dict for broadcasting."""
    return {
        "type": "state",
        "board": _board_to_list(snap.board),
        "black": _player_to_dict(snap.black),
        "white": _player_to_dict(snap.white),
        "game_over": snap.game_over,
        "game_start_time": game_start_time,
        "winner_name": winner_name,
    }


def dict_to_snapshot(d: dict) -> tuple:
    """Converts a received dict back to (GameSnapshot, game_start_time, winner_name)."""
    board = _list_to_board(d["board"])
    black = _dict_to_player(d["black"])
    white = _dict_to_player(d["white"])
    return (
        GameSnapshot(board=board, black=black, white=white, game_over=d["game_over"]),
        d.get("game_start_time", 0.0),
        d.get("winner_name", ""),
    )


def _board_to_list(board: BoardSnapshot) -> list:
    return [
        [_piece_to_dict(board.get(r, c)) for c in range(board.cols)]
        for r in range(board.rows)
    ]


def _list_to_board(rows: list) -> BoardSnapshot:
    grid = tuple(tuple(_dict_to_piece(cell) for cell in row) for row in rows)
    return BoardSnapshot(grid=grid, rows=len(rows), cols=len(rows[0]) if rows else 0)


def _piece_to_dict(piece: PieceSnapshot | None) -> dict | None:
    if piece is None:
        return None
    return {
        "color":               piece.color.value,
        "ptype":               piece.ptype.value,
        "state":               piece.state.value,
        "cooldown_ends_at":    piece.cooldown_ends_at,
        "cooldown_started_at": piece.cooldown_started_at,
        "jump_started_at":     piece.jump_started_at,
    }


def _dict_to_piece(d: dict | None) -> PieceSnapshot | None:
    if d is None:
        return None
    return PieceSnapshot(
        color=Color(d["color"]),
        ptype=PieceType(d["ptype"]),
        state=PieceState(d["state"]),
        cooldown_ends_at=d["cooldown_ends_at"],
        cooldown_started_at=d["cooldown_started_at"],
        jump_started_at=d["jump_started_at"],
    )


def _player_to_dict(player: PlayerSnapshot) -> dict:
    return {
        "name":     player.name,
        "color":    player.color.value,
        "score":    player.score,
        "moves":    list(player.moves),
        "captured": [p.value for p in player.captured],
    }


def _dict_to_player(d: dict) -> PlayerSnapshot:
    return PlayerSnapshot(
        name=d["name"],
        color=Color(d["color"]),
        score=d["score"],
        moves=tuple(tuple(m) for m in d["moves"]),
        captured=tuple(PieceType(p) for p in d["captured"]),
    )
