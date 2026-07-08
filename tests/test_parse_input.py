import pytest
from main import parse_input
from unittest.mock import patch
import io


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


class TestMain:
    def _run_main(self, stdin_text):
        from main import main
        with patch("sys.stdin", io.StringIO(stdin_text)):
            main()

    def test_main_invalid_board_exits_early(self, capsys):
        self._run_main("Board:\nxx .\nCommands:\nprint board\n")
        out = capsys.readouterr().out
        assert "wK" not in out

    def test_main_print_board(self, capsys):
        self._run_main("Board:\nwK .\n. bK\nCommands:\nprint board\n")
        out = capsys.readouterr().out
        assert "wK" in out

    def test_main_wait_then_move(self, capsys):
        self._run_main(
            "Board:\nwR . .\nCommands:\nclick 50 50\nclick 250 50\nwait 1000\nprint board\n"
        )
        out = capsys.readouterr().out
        assert ". . wR" in out

