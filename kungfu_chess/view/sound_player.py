import os
import threading
import ctypes
from kungfu_chess.shared.bus import EventBus, EventType

_SOUNDS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sounds")
)
_alias_counter = 0
_alias_lock = threading.Lock()


def _play(name: str) -> None:
    path = os.path.join(_SOUNDS_DIR, name)
    if os.path.exists(path):
        threading.Thread(target=_play_mci, args=(path,), daemon=True).start()


def _play_mci(path: str) -> None:
    global _alias_counter
    try:
        winmm = ctypes.windll.winmm
        with _alias_lock:
            _alias_counter += 1
            alias = f"snd{_alias_counter}"
        winmm.mciSendStringW(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
        winmm.mciSendStringW(f'play {alias} wait', None, 0, None)
        winmm.mciSendStringW(f'close {alias}', None, 0, None)
    except Exception:
        pass


def play_error() -> None:
    _play("error.mp3")


def init_sounds(bus: EventBus) -> None:
    """Subscribes all game events to their corresponding sound files."""
    bus.subscribe(EventType.PIECE_MOVED,    lambda **_: _play("click.mp3"))
    bus.subscribe(EventType.PIECE_CAPTURED, lambda **_: _play("eat.mp3"))
    bus.subscribe(EventType.PIECE_JUMPED,   lambda **_: _play("jump.mp3"))
    bus.subscribe(EventType.GAME_OVER,      lambda **_: _play("game_over.mp3"))
