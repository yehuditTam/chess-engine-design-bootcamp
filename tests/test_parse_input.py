import pytest
from main import parse_input


class TestParseInput:
    def test_basic_parse(self):
        lines = ["Board:", "wK .", ". bK", "Commands:", "print board"]
        board, cmds = parse_input(lines)
        assert board == [["wK", "."], [".", "bK"]]
        assert cmds == ["print board"]

    def test_empty_lines_ignored(self):
        lines = ["Board:", "", "wK .", "", "Commands:", "", "print board"]
        board, cmds = parse_input(lines)
        assert board == [["wK", "."]]
        assert cmds == ["print board"]

    def test_multiple_commands(self):
        lines = ["Board:", "wK .", "Commands:", "click 0 0", "click 100 0", "print board"]
        _, cmds = parse_input(lines)
        assert len(cmds) == 3

    def test_no_board_section(self):
        lines = ["Commands:", "print board"]
        board, cmds = parse_input(lines)
        assert board == []
        assert cmds == ["print board"]

    def test_no_commands_section(self):
        lines = ["Board:", "wK ."]
        board, cmds = parse_input(lines)
        assert board == [["wK", "."]]
        assert cmds == []

    def test_empty_input(self):
        board, cmds = parse_input([])
        assert board == []
        assert cmds == []
