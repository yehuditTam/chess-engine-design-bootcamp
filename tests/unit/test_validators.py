import pytest
from kungfu_chess.model.board import Board
from kungfu_chess.model.position import Position
from kungfu_chess.rules.rule_engine import RuleEngine
from kungfu_chess.shared.validators import validate_board, ValidationError
from kungfu_chess.shared.exceptions import OutOfBoundsError, BlockedPathError, FriendlyFireError


SIMPLE_BOARD = [
    ['.', '.', '.', '.'],
    ['.', 'wR', '.', '.'],
    ['.', '.', '.', '.'],
    ['.', '.', '.', 'bK'],
]


def p(r, c):
    return Position(r, c)


def make_validator(rows):
    board = Board(rows)
    return RuleEngine(board), board


class TestMoveValidator:
    def test_legal_rook_move(self):
        v, board = make_validator(SIMPLE_BOARD)
        piece = board.grid[1][1]
        assert v.is_legal(p(1,1), p(1,3), piece)

    def test_rook_blocked(self):
        v, board = make_validator([['wR', 'wN', '.', '.']])
        piece = board.grid[0][0]
        with pytest.raises(BlockedPathError):
            v.is_legal(p(0,0), p(0,3), piece)

    def test_capture_enemy(self):
        v, board = make_validator(SIMPLE_BOARD)
        piece = board.grid[1][1]
        assert v.is_legal(p(1,1), p(3,1), piece)

    def test_cannot_capture_own(self):
        v, board = make_validator([['wR', '.', 'wK', '.']])
        piece = board.grid[0][0]
        with pytest.raises(FriendlyFireError):
            v.is_legal(p(0,0), p(0,2), piece)

    def test_out_of_bounds(self):
        v, board = make_validator(SIMPLE_BOARD)
        piece = board.grid[1][1]
        with pytest.raises(OutOfBoundsError):
            v.is_legal(p(1,1), p(10,10), piece)

    def test_move_to_same_cell_illegal(self):
        v, board = make_validator(SIMPLE_BOARD)
        piece = board.grid[1][1]  # wR
        with pytest.raises(Exception):
            v.is_legal(p(1,1), p(1,1), piece)

    def test_clear_horizontal(self):
        v, _ = make_validator(SIMPLE_BOARD)
        assert v._is_path_clear(p(1,1), p(1,3))

    def test_blocked_horizontal(self):
        v, _ = make_validator([['wR', 'wN', '.', '.']])
        assert not v._is_path_clear(p(0,0), p(0,3))

    def test_clear_vertical(self):
        v, _ = make_validator([['.', '.'], ['.', '.'], ['.', '.'], ['.', '.']])
        assert v._is_path_clear(p(0,1), p(3,1))

    def test_blocked_vertical(self):
        v, _ = make_validator([['.'], ['wR'], ['.'], ['.']])
        assert not v._is_path_clear(p(0,0), p(3,0))

    def test_clear_diagonal(self):
        v, _ = make_validator([['.', '.', '.'], ['.', '.', '.'], ['.', '.', '.']])
        assert v._is_path_clear(p(0,0), p(2,2))


class TestValidateBoard:
    def test_valid_board(self):
        assert validate_board([['wK', '.'], ['.', 'bK']]) == []

    def test_all_dots(self):
        assert validate_board([['.','.'],['.','.']]) == []

    def test_single_cell(self):
        assert validate_board([['wQ']]) == []

    def test_empty_input(self):
        errors = validate_board([])
        assert len(errors) == 1
        assert errors[0].code == "EMPTY_BOARD"

    def test_unequal_row_widths(self):
        errors = validate_board([['wK', '.'], ['.']])
        assert any(e.code == "ROW_WIDTH_MISMATCH" for e in errors)
        assert any(e.row == 1 for e in errors)

    def test_first_row_narrower_than_second(self):
        errors = validate_board([['wK'], ['wQ', '.']])
        assert any(e.code == "ROW_WIDTH_MISMATCH" for e in errors)
        assert any(e.row == 1 for e in errors)

    def test_unknown_token(self):
        errors = validate_board([['wK', 'xZ']])
        assert any(e.code == "UNKNOWN_TOKEN" for e in errors)
        assert any(e.token == 'xZ' for e in errors)
        assert any(e.row == 0 for e in errors)

    def test_lowercase_token(self):
        errors = validate_board([['wk']])
        assert any(e.code == "UNKNOWN_TOKEN" for e in errors)

    def test_empty_string_token(self):
        errors = validate_board([['wK', '']])
        assert any(e.code == "UNKNOWN_TOKEN" for e in errors)

    def test_multiple_errors_all_reported(self):
        errors = validate_board([['wK', 'xZ'], ['xx', '.']])
        assert len(errors) == 2
        assert all(e.code == "UNKNOWN_TOKEN" for e in errors)

    def test_error_str_includes_row_and_token(self):
        errors = validate_board([['wK', 'xZ']])
        s = str(errors[0])
        assert 'UNKNOWN_TOKEN' in s
        assert 'row=0' in s
        assert 'token=xZ' in s
