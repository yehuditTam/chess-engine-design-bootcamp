import json
import pytest
from kungfu_chess.shared.dto import (
    GameSnapshot, BoardSnapshot, PlayerSnapshot, PieceSnapshot
)
from kungfu_chess.shared.constants import Color, PieceType, PieceState
from server.serializer import snapshot_to_dict, dict_to_snapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_piece(color=Color.WHITE, ptype=PieceType.ROOK, state=PieceState.IDLE,
               is_cooling=False, is_airborne=False,
               cooldown_ends_at=0.0, cooldown_started_at=0.0, jump_started_at=0.0):
    return PieceSnapshot(
        color=color, ptype=ptype, state=state,
        is_cooling=is_cooling, is_airborne=is_airborne,
        cooldown_ends_at=cooldown_ends_at,
        cooldown_started_at=cooldown_started_at,
        jump_started_at=jump_started_at,
    )


def make_player(name="Alice", color=Color.BLACK, score=0, moves=(), captured=()):
    return PlayerSnapshot(name=name, color=color, score=score,
                          moves=moves, captured=captured)


def make_snapshot(grid=None, black=None, white=None):
    if grid is None:
        grid = ((make_piece(), None), (None, None))
    board = BoardSnapshot(grid=grid, rows=len(grid), cols=len(grid[0]))
    return GameSnapshot(
        board=board,
        black=black or make_player("Black", Color.BLACK),
        white=white or make_player("White", Color.WHITE),
    )


# ---------------------------------------------------------------------------
# snapshot_to_dict
# ---------------------------------------------------------------------------

class TestSnapshotToDict:
    def test_type_field_is_state(self):
        d = snapshot_to_dict(make_snapshot(), game_over=False)
        assert d["type"] == "state"

    def test_game_over_false(self):
        d = snapshot_to_dict(make_snapshot(), game_over=False)
        assert d["game_over"] is False

    def test_game_over_true(self):
        d = snapshot_to_dict(make_snapshot(), game_over=True)
        assert d["game_over"] is True

    def test_board_dimensions(self):
        d = snapshot_to_dict(make_snapshot(), game_over=False)
        assert len(d["board"]) == 2
        assert len(d["board"][0]) == 2

    def test_piece_fields_present(self):
        d = snapshot_to_dict(make_snapshot(), game_over=False)
        piece = d["board"][0][0]
        assert piece["color"] == "w"
        assert piece["ptype"] == "R"
        assert piece["state"] == "idle"
        assert piece["is_cooling"] is False
        assert piece["is_airborne"] is False

    def test_empty_cell_is_none(self):
        d = snapshot_to_dict(make_snapshot(), game_over=False)
        assert d["board"][0][1] is None

    def test_player_fields(self):
        d = snapshot_to_dict(make_snapshot(), game_over=False)
        assert d["black"]["name"] == "Black"
        assert d["black"]["color"] == "b"
        assert d["black"]["score"] == 0
        assert d["white"]["name"] == "White"

    def test_player_score(self):
        snap = make_snapshot(white=make_player("Bob", Color.WHITE, score=9))
        d = snapshot_to_dict(snap, game_over=False)
        assert d["white"]["score"] == 9

    def test_captured_serialised_as_strings(self):
        snap = make_snapshot(
            black=make_player(captured=(PieceType.ROOK, PieceType.PAWN))
        )
        d = snapshot_to_dict(snap, game_over=False)
        assert d["black"]["captured"] == ["R", "P"]

    def test_result_is_json_serialisable(self):
        d = snapshot_to_dict(make_snapshot(), game_over=False)
        json.dumps(d)  # should not raise

    def test_cooling_piece(self):
        piece = make_piece(state=PieceState.COOLING, is_cooling=True,
                           cooldown_ends_at=123.4, cooldown_started_at=120.0)
        grid = ((piece, None), (None, None))
        d = snapshot_to_dict(make_snapshot(grid=grid), game_over=False)
        p = d["board"][0][0]
        assert p["state"] == "cooling"
        assert p["is_cooling"] is True
        assert p["cooldown_ends_at"] == pytest.approx(123.4)

    def test_airborne_piece(self):
        piece = make_piece(is_airborne=True, jump_started_at=50.0)
        grid = ((piece, None), (None, None))
        d = snapshot_to_dict(make_snapshot(grid=grid), game_over=False)
        p = d["board"][0][0]
        assert p["is_airborne"] is True
        assert p["jump_started_at"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# dict_to_snapshot (round-trip)
# ---------------------------------------------------------------------------

class TestDictToSnapshot:
    def _round_trip(self, snap, game_over=False):
        d = snapshot_to_dict(snap, game_over=game_over)
        snap_out, go, _, _ = dict_to_snapshot(d)
        return snap_out, go

    def test_round_trip_game_over(self):
        _, go = self._round_trip(make_snapshot(), game_over=True)
        assert go is True

    def test_round_trip_board_dimensions(self):
        snap, _ = self._round_trip(make_snapshot())
        assert snap.board.rows == 2
        assert snap.board.cols == 2

    def test_round_trip_piece_color(self):
        snap, _ = self._round_trip(make_snapshot())
        assert snap.board.get(0, 0).color == Color.WHITE

    def test_round_trip_piece_ptype(self):
        snap, _ = self._round_trip(make_snapshot())
        assert snap.board.get(0, 0).ptype == PieceType.ROOK

    def test_round_trip_empty_cell(self):
        snap, _ = self._round_trip(make_snapshot())
        assert snap.board.get(0, 1) is None

    def test_round_trip_player_name(self):
        snap, _ = self._round_trip(make_snapshot())
        assert snap.black.name == "Black"
        assert snap.white.name == "White"

    def test_round_trip_player_score(self):
        orig = make_snapshot(white=make_player("Bob", Color.WHITE, score=14))
        snap, _ = self._round_trip(orig)
        assert snap.white.score == 14

    def test_round_trip_captured(self):
        orig = make_snapshot(
            black=make_player(captured=(PieceType.QUEEN,))
        )
        snap, _ = self._round_trip(orig)
        assert PieceType.QUEEN in snap.black.captured

    def test_round_trip_cooling_fields(self):
        piece = make_piece(state=PieceState.COOLING, is_cooling=True,
                           cooldown_ends_at=200.0, cooldown_started_at=195.0)
        grid = ((piece, None), (None, None))
        snap, _ = self._round_trip(make_snapshot(grid=grid))
        p = snap.board.get(0, 0)
        assert p.state == PieceState.COOLING
        assert p.is_cooling is True
        assert p.cooldown_ends_at == pytest.approx(200.0)

    def test_round_trip_via_json_string(self):
        """Simulate real network: serialize → JSON string → deserialize."""
        d = snapshot_to_dict(make_snapshot(), game_over=False)
        json_str = json.dumps(d)
        restored = json.loads(json_str)
        snap, go, _, _ = dict_to_snapshot(restored)
        assert snap.board.get(0, 0).ptype == PieceType.ROOK
        assert go is False
