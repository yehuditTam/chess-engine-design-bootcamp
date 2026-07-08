import pytest
from validators import validate_board


class TestValidateBoard:
    def test_valid_board(self):
        assert validate_board([['wK', '.'], ['.', 'bK']])

    def test_all_dots(self):
        assert validate_board([['.','.'],['.','.']]) 

    def test_single_cell(self):
        assert validate_board([['wQ']])

    def test_empty_input(self):
        assert not validate_board([])

    def test_unequal_row_widths(self):
        assert not validate_board([['wK', '.'], ['.']])

    def test_unknown_token(self):
        assert not validate_board([['wK', 'xZ']])

    def test_lowercase_token(self):
        assert not validate_board([['wk']])

    def test_empty_string_token(self):
        assert not validate_board([['wK', '']])
