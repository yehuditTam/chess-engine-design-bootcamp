"""
Serializer — converts between GameSnapshot (Python objects) and JSON-friendly dicts.

Used by:
  - server: snapshot_to_dict() before broadcasting to clients
  - client: dict_to_snapshot() after receiving from server
"""

from kungfu_chess.shared.dto import (
    GameSnapshot, BoardSnapshot, PlayerSnapshot, PieceSnapshot
)
from kungfu_chess.shared.constants import Color, PieceType, PieceState


# ---------------------------------------------------------------------------
# Snapshot → dict  (server side, before json.dumps)
# ---------------------------------------------------------------------------

def snapshot_to_dict(snap: GameSnapshot, game_over: bool,
                     game_start_time: float = 0.0,
                     winner_name: str = "") -> dict:
    """Convert a GameSnapshot to a JSON-serialisable dict."""
    return {
        "type": "state",
        "board": _board_to_list(snap.board),
        "black": _player_to_dict(snap.black),
        "white": _player_to_dict(snap.white),
        "game_over": game_over,
        "game_start_time": game_start_time,
        "winner_name": winner_name,
    }


def _board_to_list(board: BoardSnapshot) -> list:
    return [
        [_piece_to_dict(board.get(r, c)) for c in range(board.cols)]
        for r in range(board.rows)
    ]


def _piece_to_dict(piece: PieceSnapshot | None) -> dict | None:
    if piece is None:
        return None
    return {
        "color": piece.color.value,          # "w" / "b"
        "ptype": piece.ptype.value,           # "K", "Q", "R", ...
        "state": piece.state.value,           # "idle", "moving", "cooling", "captured"
        "is_cooling": piece.is_cooling,
        "is_airborne": piece.is_airborne,
        "cooldown_ends_at": piece.cooldown_ends_at,
        "cooldown_started_at": piece.cooldown_started_at,
        "jump_started_at": piece.jump_started_at,
    }


def _player_to_dict(player: PlayerSnapshot) -> dict:
    return {
        "name": player.name,
        "color": player.color.value,
        "score": player.score,
        "moves": list(player.moves),          # list of (time_str, move_str)
        "captured": [p.value for p in player.captured],  # list of ptype strings
    }


# ---------------------------------------------------------------------------
# dict → Snapshot  (client side, after json.loads)
# ---------------------------------------------------------------------------

def dict_to_snapshot(d: dict) -> tuple:
    """
    Convert a received dict back to (GameSnapshot, game_over, game_start_time, winner_name).
    """
    board = _list_to_board(d["board"])
    black = _dict_to_player(d["black"])
    white = _dict_to_player(d["white"])
    game_over = d["game_over"]
    game_start_time = d.get("game_start_time", 0.0)
    winner_name = d.get("winner_name", "")
    return (
        GameSnapshot(board=board, black=black, white=white),
        game_over, game_start_time, winner_name
    )


def _list_to_board(rows: list) -> BoardSnapshot:
    grid = tuple(
        tuple(_dict_to_piece(cell) for cell in row)
        for row in rows
    )
    return BoardSnapshot(
        grid=grid,
        rows=len(rows),
        cols=len(rows[0]) if rows else 0,
    )


def _dict_to_piece(d: dict | None) -> PieceSnapshot | None:
    if d is None:
        return None
    return PieceSnapshot(
        color=Color(d["color"]),
        ptype=PieceType(d["ptype"]),
        state=PieceState(d["state"]),
        is_cooling=d["is_cooling"],
        is_airborne=d["is_airborne"],
        cooldown_ends_at=d["cooldown_ends_at"],
        cooldown_started_at=d["cooldown_started_at"],
        jump_started_at=d["jump_started_at"],
    )


def _dict_to_player(d: dict) -> PlayerSnapshot:
    return PlayerSnapshot(
        name=d["name"],
        color=Color(d["color"]),
        score=d["score"],
        moves=tuple(tuple(m) for m in d["moves"]),
        captured=tuple(PieceType(p) for p in d["captured"]),
    )
