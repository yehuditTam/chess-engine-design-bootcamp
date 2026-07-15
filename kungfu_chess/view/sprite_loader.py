import json
import time
import pathlib
import cv2
import numpy as np

PIECES_DIR = pathlib.Path(__file__).parent.parent.parent / "assets" / "pieces_mine"
BOARD_PATH  = pathlib.Path(__file__).parent.parent.parent / "assets" / "board.png"

_STATE_MAP = {
    'idle':    'idle',
    'moving':  'move',
    'cooling': 'long_rest',
    'captured':'idle',
    'jumping': 'jump',
}


def _load_img(path) -> np.ndarray:
    buf = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_UNCHANGED)


def _prepare_sprite(img: np.ndarray, size: int) -> np.ndarray:
    if img.shape[2] == 4:
        bgra = img
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        bgra = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
        bgra[:, :, 3] = mask
    return cv2.resize(bgra, (size, size), interpolation=cv2.INTER_AREA)


class SpriteLoader:
    def __init__(self):
        self._board_cache: dict[int, np.ndarray] = {}
        self._frames_cache: dict[tuple, tuple] = {}
        self._sprite_cache: dict[tuple, np.ndarray] = {}

    def load_board_img(self, size: int) -> np.ndarray:
        if size not in self._board_cache:
            img = _load_img(BOARD_PATH)
            if img.shape[2] == 4:
                img = img[:, :, :3]
            img = img[2:-2, 2:-2]
            self._board_cache[size] = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
        return self._board_cache[size]

    def _load_frames(self, folder: str, state: str) -> tuple:
        key = (folder, state)
        if key not in self._frames_cache:
            state_dir = PIECES_DIR / folder / "states" / state
            cfg_path = state_dir / "config.json"
            fps, is_loop = 6, True
            if cfg_path.exists():
                with open(cfg_path) as f:
                    cfg = json.load(f)["graphics"]
                    fps = cfg["frames_per_sec"]
                    is_loop = cfg.get("is_loop", True)
            paths = sorted((state_dir / "sprites").glob("*.png"), key=lambda p: int(p.stem))
            self._frames_cache[key] = ([_load_img(p) for p in paths], fps, is_loop)
        return self._frames_cache[key]

    def load_piece_sprite(self, ptype_value: str, color_value: str, size: int,
                          state: str = 'idle', anim_offset: float = 0.0) -> np.ndarray:
        anim_state = _STATE_MAP.get(state, 'idle')
        folder = color_value[0].lower() + ptype_value.upper()
        frames, fps, is_loop = self._load_frames(folder, anim_state)
        if not frames:
            return _prepare_sprite(_load_img(PIECES_DIR / folder / "states" / "idle" / "sprites" / "1.png"), size)
        frame_idx = int((time.time() + anim_offset) * fps)
        frame_idx = frame_idx % len(frames) if is_loop else min(frame_idx, len(frames) - 1)
        cache_key = (ptype_value, color_value, size, anim_state, frame_idx)
        if cache_key not in self._sprite_cache:
            self._sprite_cache[cache_key] = _prepare_sprite(frames[frame_idx], size)
        return self._sprite_cache[cache_key]
