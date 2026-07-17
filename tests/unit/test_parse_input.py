import pytest
from kungfu_chess.io.board_parser import parse_input
from kungfu_chess.io.board_parser import load_board_csv, TextInputParser
from unittest.mock import patch
import io
import tempfile
import os


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


class TestBoardMapper:
    def test_jump_command_parsed(self):
        from kungfu_chess.input.board_mapper import parse
        from kungfu_chess.input.commands import JumpCommand
        cmd = parse("jump 100 200")
        assert isinstance(cmd, JumpCommand)

    def test_unknown_command_raises(self):
        from kungfu_chess.input.board_mapper import parse
        with pytest.raises(ValueError):
            parse("fly 100 200")


class TestMain:
    def _run_main(self, stdin_text):
        from kungfu_chess.input.controller import main
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
            "Board:\nwR . .\nCommands:\nclick 50 50\nclick 250 50\nwait 2000\nprint board\n"
        )
        out = capsys.readouterr().out
        assert ". . wR" in out


class TestLoadBoardCsv:
    def test_loads_pieces_correctly(self):
        content = "RW,PB,.\n.,KB,.\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            path = f.name
        try:
            rows = load_board_csv(path)
            assert rows[0] == ['wR', 'bP', '.']
            assert rows[1] == ['.', 'bK', '.']
        finally:
            os.unlink(path)

    def test_empty_cells_become_dots(self):
        content = ".,.,KW\n"
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(content)
            path = f.name
        try:
            rows = load_board_csv(path)
            assert rows[0][0] == '.'
            assert rows[0][1] == '.'
            assert rows[0][2] == 'wK'
        finally:
            os.unlink(path)


class TestTextInputParser:
    def test_parse_returns_board_and_commands(self):
        raw = "Board:\nwK .\nCommands:\nprint board\n"
        board, cmds = TextInputParser().parse(raw)
        assert board == [['wK', '.']]
        assert cmds == ['print board']
