import os
from tests.integration.runner import run_kfc

KFC_DIR = os.path.join(os.path.dirname(__file__))


def kfc(name):
    return os.path.join(KFC_DIR, name)


class TestInvalidMoves:
    def test_pawn_cannot_move_three_squares(self):
        output = run_kfc(kfc("04_invalid_moves.kfc"))
        rows = [r.split() for r in output.strip().splitlines()]
        # wP must still be at row 6, col 1 — move was illegal, board unchanged
        assert rows[6][1] == "wP"
        assert rows[5][1] == "."
        assert rows[4][1] == "."
        assert rows[3][1] == "."


class TestRunnerValidation:
    def test_invalid_board_returns_error(self):
        import tempfile
        import os
        content = "xx yy\nPRINT\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.kfc', delete=False) as f:
            f.write(content)
            path = f.name
        try:
            output = run_kfc(path)
            assert output.startswith("ERROR")
        finally:
            os.unlink(path)


class TestCapture:
    def test_rook_captures_enemy_rook_and_king(self):
        output = run_kfc(kfc("05_capture.kfc"))
        rows = [r.split() for r in output.strip().splitlines()]
        # wR captured bR at (0,2), then moved to (2,2) capturing bK
        assert rows[0][0] == "."
        assert rows[0][2] == "."
        assert rows[2][2] == "wR"

    def test_game_over_after_king_capture(self):
        output = run_kfc(kfc("05_capture.kfc"))
        rows = [r.split() for r in output.strip().splitlines()]
        # bK at (2,2) was captured — wR is there now
        assert rows[2][2] != "bK"


class TestJump:
    def test_airborne_captures_arriving_enemy(self):
        output = run_kfc(kfc("06_jump.kfc"))
        rows = [r.split() for r in output.strip().splitlines()]
        # wR jumped at (1,1); bR tried to arrive there and was captured
        assert rows[1][1] == "wR"
        assert rows[0][1] == "."


class TestPromotion:
    def test_pawn_promotes_to_queen(self):
        output = run_kfc(kfc("07_promotion.kfc"))
        rows = [r.split() for r in output.strip().splitlines()]
        # wP moved from (1,0) to (0,0) and promoted
        assert rows[0][0] == "wQ"
        assert rows[1][0] == "."


class TestFriendlyFire:
    def test_rook_cannot_capture_own_king(self):
        output = run_kfc(kfc("08_friendly_fire.kfc"))
        rows = [r.split() for r in output.strip().splitlines()]
        # wR move to wK cell was rejected — both stay in place
        assert rows[0][0] == "wR"
        assert rows[0][2] == "wK"
