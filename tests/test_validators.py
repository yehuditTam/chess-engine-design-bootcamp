import pytest
from validators import validate_board, ValidationError


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
