import threading
from kungfu_chess.shared.bus import EventBus, EventType

_SOUNDS_DIR = "assets/sounds"


def _play(name):
    try:
        from playsound import playsound
        threading.Thread(target=playsound, args=(f"{_SOUNDS_DIR}/{name}",), daemon=True).start()
    except Exception:
        pass


def play_error():
    _play("error.mp3")


def init_sounds(bus: EventBus) -> None:
    bus.subscribe(EventType.PIECE_MOVED, lambda **_: _play("click.mp3"))
    bus.subscribe(EventType.PIECE_CAPTURED, lambda **_: _play("eat.mp3"))
    bus.subscribe(EventType.PIECE_JUMPED, lambda **_: _play("jump.mp3"))
    bus.subscribe(EventType.GAME_OVER, lambda **_: _play("game_over.mp3"))
