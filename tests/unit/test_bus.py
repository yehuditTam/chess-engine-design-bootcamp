import time
import pytest
from kungfu_chess.shared.bus import EventBus, EventType
from kungfu_chess.realtime.game_engine import GameEngine
from kungfu_chess.model.position import Position
from kungfu_chess.shared.constants import Color, PieceType


def p(r, c):
    return Position(r, c)


# ---------------------------------------------------------------------------
# Unit tests for EventBus itself
# ---------------------------------------------------------------------------

class TestEventBusSubscribePublish:
    def test_subscriber_called_on_publish(self):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.PIECE_MOVED, lambda **kw: received.append(kw))
        bus.publish(EventType.PIECE_MOVED, color=Color.WHITE, ptype=PieceType.ROOK,
                    start=p(0, 0), end=p(0, 1))
        assert len(received) == 1
        assert received[0]["color"] == Color.WHITE

    def test_multiple_subscribers_all_called(self):
        bus = EventBus()
        log1, log2 = [], []
        bus.subscribe(EventType.PIECE_MOVED, lambda **kw: log1.append(kw))
        bus.subscribe(EventType.PIECE_MOVED, lambda **kw: log2.append(kw))
        bus.publish(EventType.PIECE_MOVED, color=Color.BLACK, ptype=PieceType.PAWN,
                    start=p(1, 0), end=p(2, 0))
        assert len(log1) == 1
        assert len(log2) == 1

    def test_subscriber_for_different_event_not_called(self):
        bus = EventBus()
        called = []
        bus.subscribe(EventType.GAME_OVER, lambda **kw: called.append(kw))
        bus.publish(EventType.PIECE_MOVED, color=Color.WHITE, ptype=PieceType.ROOK,
                    start=p(0, 0), end=p(0, 1))
        assert called == []

    def test_no_subscribers_publish_does_not_raise(self):
        bus = EventBus()
        bus.publish(EventType.PIECE_CAPTURED, by_color=Color.WHITE,
                    captured_ptype=PieceType.PAWN)

    def test_publish_passes_kwargs_correctly(self):
        bus = EventBus()
        received = {}
        bus.subscribe(EventType.GAME_OVER, lambda **kw: received.update(kw))
        bus.publish(EventType.GAME_OVER, winner_color=Color.BLACK)
        assert received["winner_color"] == Color.BLACK

    def test_subscribe_same_event_multiple_times(self):
        bus = EventBus()
        count = []
        cb = lambda **kw: count.append(1)
        bus.subscribe(EventType.PIECE_JUMPED, cb)
        bus.subscribe(EventType.PIECE_JUMPED, cb)
        bus.publish(EventType.PIECE_JUMPED, color=Color.WHITE, cell=p(0, 0))
        assert len(count) == 2

    def test_clear_removes_all_subscribers(self):
        bus = EventBus()
        called = []
        bus.subscribe(EventType.PIECE_MOVED, lambda **kw: called.append(1))
        bus.clear()
        bus.publish(EventType.PIECE_MOVED, color=Color.WHITE, ptype=PieceType.ROOK,
                    start=p(0, 0), end=p(0, 1))
        assert called == []

    def test_game_started_published_on_first_move(self):
        bus = EventBus()
        started = []
        bus.subscribe(EventType.GAME_STARTED, lambda **_: started.append(1))
        game = GameEngine([['wR', '.', 'bK']], bus=bus)
        game.request_move(p(0, 0), p(0, 1))
        assert len(started) == 1

    def test_game_started_published_only_once(self):
        bus = EventBus()
        started = []
        bus.subscribe(EventType.GAME_STARTED, lambda **_: started.append(1))
        game = GameEngine([['wR', '.', '.', 'bK']], bus=bus)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = __import__('time').time() - 1
        game.execute_pending_moves()
        game.pending_cooldowns[0].ready_at = __import__('time').time() - 1
        game.execute_pending_moves()
        game.request_move(p(0, 1), p(0, 2))
        assert len(started) == 1

    def test_score_updated_published_on_capture(self):
        bus = EventBus()
        scores = []
        bus.subscribe(EventType.SCORE_UPDATED, lambda **kw: scores.append(kw))
        game = GameEngine([['wR', '.', 'bR', 'bK']], bus=bus)
        game.request_move(p(0, 0), p(0, 2))
        game.pending_moves[0].arrive_at = __import__('time').time() - 1
        game.execute_pending_moves()
        assert len(scores) == 1
        assert scores[0]["color"] == Color.WHITE
        assert scores[0]["score"] == 5
        assert scores[0]["captured_ptype"] == PieceType.ROOK

    def test_move_logged_published_on_arrival(self):
        bus = EventBus()
        logs = []
        bus.subscribe(EventType.MOVE_LOGGED, lambda **kw: logs.append(kw))
        game = GameEngine([['wR', '.', 'bK']], bus=bus)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = __import__('time').time() - 1
        game.execute_pending_moves()
        assert len(logs) == 1
        assert logs[0]["color"] == Color.WHITE
        assert 'R' in logs[0]["move_str"]


# ---------------------------------------------------------------------------
# Integration tests: GameEngine publishes correct events
# ---------------------------------------------------------------------------

BOARD_ROOKS = [
    ['wR', '.', '.'],
    ['.', '.', '.'],
    ['bR', '.', '.'],
]

BOARD_KING_CAPTURE = [
    ['wR', '.', 'bK'],
    ['.', '.', '.'],
    ['.', '.', 'wK'],
]

BOARD_JUMP = [
    ['.', 'bR', '.'],
    ['.', 'wR', '.'],
    ['.', '.', '.'],
]


class TestGameEnginePublishesMoved:
    def test_piece_moved_published_on_arrival(self):
        bus = EventBus()
        moved = []
        bus.subscribe(EventType.PIECE_MOVED, lambda **kw: moved.append(kw))
        game = GameEngine(BOARD_ROOKS, bus=bus)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert len(moved) == 1
        assert moved[0]["color"] == Color.WHITE
        assert moved[0]["ptype"] == PieceType.ROOK
        assert moved[0]["start"] == p(0, 0)
        assert moved[0]["end"] == p(0, 1)

    def test_piece_moved_not_published_before_arrival(self):
        bus = EventBus()
        moved = []
        bus.subscribe(EventType.PIECE_MOVED, lambda **kw: moved.append(kw))
        game = GameEngine(BOARD_ROOKS, bus=bus)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() + 999
        game.execute_pending_moves()
        assert moved == []


class TestGameEnginePublishesCaptured:
    def test_piece_captured_published_on_capture(self):
        bus = EventBus()
        captures = []
        bus.subscribe(EventType.PIECE_CAPTURED, lambda **kw: captures.append(kw))
        game = GameEngine(BOARD_ROOKS, bus=bus)
        game.request_move(p(0, 0), p(2, 0))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert len(captures) == 1
        assert captures[0]["by_color"] == Color.WHITE
        assert captures[0]["captured_ptype"] == PieceType.ROOK

    def test_piece_captured_not_published_on_plain_move(self):
        bus = EventBus()
        captures = []
        bus.subscribe(EventType.PIECE_CAPTURED, lambda **kw: captures.append(kw))
        game = GameEngine(BOARD_ROOKS, bus=bus)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert captures == []


class TestGameEnginePublishesGameOver:
    def test_game_over_published_on_king_capture(self):
        bus = EventBus()
        game_overs = []
        bus.subscribe(EventType.GAME_OVER, lambda **kw: game_overs.append(kw))
        game = GameEngine(BOARD_KING_CAPTURE, bus=bus)
        game.request_move(p(0, 0), p(0, 2))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert len(game_overs) == 1
        assert game_overs[0]["winner_color"] == Color.WHITE

    def test_game_over_not_published_on_non_king_capture(self):
        bus = EventBus()
        game_overs = []
        bus.subscribe(EventType.GAME_OVER, lambda **kw: game_overs.append(kw))
        game = GameEngine(BOARD_ROOKS, bus=bus)
        game.request_move(p(0, 0), p(2, 0))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert game_overs == []

    def test_winner_is_opposite_of_captured_king_color(self):
        bus = EventBus()
        game_overs = []
        bus.subscribe(EventType.GAME_OVER, lambda **kw: game_overs.append(kw))
        board = [
            ['bR', '.', 'wK'],
            ['.', '.', '.'],
            ['.', '.', 'bK'],
        ]
        game = GameEngine(board, bus=bus)
        game.request_move(p(0, 0), p(0, 2))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert game_overs[0]["winner_color"] == Color.BLACK


class TestGameEnginePublishesJump:
    def test_jump_event_published(self):
        bus = EventBus()
        jumps = []
        bus.subscribe(EventType.PIECE_JUMPED, lambda **kw: jumps.append(kw))
        game = GameEngine(BOARD_JUMP, bus=bus)
        game.handle_jump(p(1, 1))
        assert len(jumps) == 1
        assert jumps[0]["color"] == Color.WHITE
        assert jumps[0]["cell"] == p(1, 1)

    def test_jump_event_not_published_for_invalid_jump(self):
        bus = EventBus()
        jumps = []
        bus.subscribe(EventType.PIECE_JUMPED, lambda **kw: jumps.append(kw))
        game = GameEngine(BOARD_JUMP, bus=bus)
        game.request_move(p(1, 1), p(2, 1))  # piece is now pending
        game.handle_jump(p(1, 1))             # should be rejected
        assert jumps == []


class TestGameEngineNoBus:
    def test_game_works_without_explicit_bus(self):
        """Passing no bus should not raise — uses internal default EventBus."""
        game = GameEngine(BOARD_ROOKS)
        game.request_move(p(0, 0), p(0, 1))
        game.pending_moves[0].arrive_at = time.time() - 1
        game.execute_pending_moves()
        assert game.board.get_piece(0, 1) is not None
