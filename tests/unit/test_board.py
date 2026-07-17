import pytest
from kungfu_chess.model.board import Board
from kungfu_chess.shared.constants import PieceType, Color


SIMPLE_BOARD = [
    ['.', '.', '.', '.'],
    ['.', 'wR', '.', '.'],
    ['.', '.', '.', '.'],
    ['.', '.', '.', 'bK'],
]


class TestBoardParsing:
    def test_empty_cell_is_none(self):
        board = make_board([['.', '.'], ['.', '.']])
        assert board.grid[0][0] is None

    def test_piece_parsed_correctly(self):
        board = make_board([['wR', '.']])
        piece = board.grid[0][0]
        assert piece.color == Color.WHITE
        assert piece.ptype == PieceType.ROOK

    def test_all_piece_types_parsed(self):
        row = ['wK', 'wQ', 'wR', 'wB', 'wN', 'wP']
        board = make_board([row])
        types = [p.ptype for p in board.grid[0]]
        assert types == [PieceType.KING, PieceType.QUEEN, PieceType.ROOK,
                         PieceType.BISHOP, PieceType.KNIGHT, PieceType.PAWN]


class TestGetPiece:
    def test_empty_cell_returns_none(self):
        board = make_board(SIMPLE_BOARD)
        assert board.get_piece(0, 0) is None

    def test_occupied_cell_returns_correct_piece(self):
        board = make_board(SIMPLE_BOARD)
        piece = board.get_piece(1, 1)
        assert piece.color == Color.WHITE
        assert piece.ptype == PieceType.ROOK


class TestRemovePiece:
    def test_remove_clears_cell(self):
        board = make_board(SIMPLE_BOARD)
        board.remove_piece(1, 1)
        assert board.get_piece(1, 1) is None


class TestInBounds:
    def test_valid_cell_is_in_bounds(self):
        board = make_board(SIMPLE_BOARD)
        assert board.in_bounds(0, 0)
        assert board.in_bounds(3, 3)

    def test_out_of_bounds_cells(self):
        board = make_board(SIMPLE_BOARD)
        assert not board.in_bounds(-1, 0)
        assert not board.in_bounds(0, 4)
        assert not board.in_bounds(4, 0)

    def test_piece_moves_to_target(self):
        board = make_board(SIMPLE_BOARD)
        board.move_piece((1, 1), (1, 3))
        assert board.grid[1][3] is not None
        assert board.grid[1][1] is None

    def test_capture_replaces_target(self):
        board = make_board(SIMPLE_BOARD)
        board.move_piece((1, 1), (3, 3))
        assert board.grid[3][3].color == Color.WHITE
        assert board.grid[1][1] is None


class TestBoardSnapshot:
    def test_snapshot_returns_piece_snapshots(self):
        from kungfu_chess.shared.dto import PieceSnapshot
        board = make_board([['wR', '.']])
        snap = board.snapshot()
        assert snap.get(0, 0) == PieceSnapshot(Color.WHITE, PieceType.ROOK)
        assert snap.get(0, 1) is None

    def test_snapshot_is_immutable(self):
        from kungfu_chess.shared.dto import PieceSnapshot
        board = make_board([['wR', '.']])
        snap = board.snapshot()
        board.move_piece((0, 0), (0, 1))
        assert snap.get(0, 0) == PieceSnapshot(Color.WHITE, PieceType.ROOK)
        assert snap.get(0, 1) is None


class TestBoardDimensions:
    def test_rows_and_cols(self):
        board = make_board(SIMPLE_BOARD)
        assert board.rows() == 4
        assert board.cols() == 4

    def test_non_square_board(self):
        board = make_board([['wR', '.', '.'], ['.', '.', '.']])
        assert board.rows() == 2
        assert board.cols() == 3


class TestAddPiece:
    def test_add_piece_to_empty_cell(self):
        board = make_board([['.', '.']])
        from kungfu_chess.model.piece import Piece
        from kungfu_chess.rules.piece_rules import RookStrategy
        p = Piece(Color.WHITE, PieceType.ROOK, move_strategy=RookStrategy())
        board.add_piece(0, 0, p)
        assert board.get_piece(0, 0) is p

    def test_add_piece_to_occupied_cell_raises(self):
        board = make_board([['wR', '.']])
        from kungfu_chess.model.piece import Piece
        from kungfu_chess.rules.piece_rules import QueenStrategy
        from kungfu_chess.shared.exceptions import InvalidMoveError
        p = Piece(Color.BLACK, PieceType.QUEEN, move_strategy=QueenStrategy())
        with pytest.raises(InvalidMoveError):
            board.add_piece(0, 0, p)
