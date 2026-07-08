import pytest
from Board import Board
from constants import PieceType, Color
from exceptions import InvalidMoveError, OutOfBoundsError, BlockedPathError, FriendlyFireError


SIMPLE_BOARD = [
    ['.', '.', '.', '.'],
    ['.', 'wR', '.', '.'],
    ['.', '.', '.', '.'],
    ['.', '.', '.', 'bK'],
]


def make_board(rows):
    return Board(rows)


class TestBoardParsing:
    def test_empty_cell_is_none(self):
        board = make_board([['.', '.'],['.', '.']])
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


class TestMovePiece:
    def test_piece_moves_to_target(self):
        board = make_board(SIMPLE_BOARD)
        board.move_piece((1,1), (1,3))
        assert board.grid[1][3] is not None
        assert board.grid[1][1] is None

    def test_capture_replaces_target(self):
        board = make_board(SIMPLE_BOARD)
        board.move_piece((1,1), (3,3))
        assert board.grid[3][3].color == Color.WHITE
        assert board.grid[1][1] is None


class TestPathClear:
    def test_clear_horizontal(self):
        board = make_board(SIMPLE_BOARD)
        assert board.is_path_clear((1,1), (1,3))

    def test_blocked_horizontal(self):
        board = make_board([['wR', 'wN', '.', '.']])
        assert not board.is_path_clear((0,0), (0,3))

    def test_clear_vertical(self):
        board = make_board([['.', '.'], ['.', '.'], ['.', '.'], ['.', '.']])
        assert board.is_path_clear((0,1), (3,1))

    def test_blocked_vertical(self):
        board = make_board([['.'], ['wR'], ['.'], ['.']])
        assert not board.is_path_clear((0,0), (3,0))

    def test_clear_diagonal(self):
        board = make_board([['.', '.', '.'], ['.', '.', '.'], ['.', '.', '.']])
        assert board.is_path_clear((0,0), (2,2))


class TestIsLegal:
    def test_legal_rook_move(self):
        board = make_board(SIMPLE_BOARD)
        piece = board.grid[1][1]
        assert board.is_legal((1,1), (1,3), piece)

    def test_rook_blocked(self):
        board = make_board([['wR', 'wN', '.', '.']])
        piece = board.grid[0][0]
        with pytest.raises(BlockedPathError):
            board.is_legal((0,0), (0,3), piece)

    def test_capture_enemy(self):
        board = make_board(SIMPLE_BOARD)
        piece = board.grid[1][1]
        assert board.is_legal((1,1), (3,1), piece)

    def test_cannot_capture_own(self):
        board = make_board([['wR', '.', 'wK', '.']])
        piece = board.grid[0][0]
        with pytest.raises(FriendlyFireError):
            board.is_legal((0,0), (0,2), piece)

    def test_out_of_bounds(self):
        board = make_board(SIMPLE_BOARD)
        piece = board.grid[1][1]
        with pytest.raises(OutOfBoundsError):
            board.is_legal((1,1), (10,10), piece)
