import hashlib
import sqlite3
import os

_DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")


def _connect():
    con = sqlite3.connect(_DB_PATH)
    con.execute(
        "CREATE TABLE IF NOT EXISTS users "
        "(username TEXT PRIMARY KEY, password_hash TEXT, rating INTEGER DEFAULT 1200)"
    )
    con.commit()
    return con


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register(username: str, password: str) -> bool:
    """Return True on success, False if username already taken."""
    try:
        with _connect() as con:
            con.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, _hash(password)),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate(username: str, password: str) -> bool:
    with _connect() as con:
        row = con.execute(
            "SELECT password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
    return row is not None and row[0] == _hash(password)


def get_rating(username: str) -> int:
    with _connect() as con:
        row = con.execute(
            "SELECT rating FROM users WHERE username = ?", (username,)
        ).fetchone()
    return row[0] if row else 1200


def update_ratings(winner: str, loser: str) -> tuple[int, int]:
    """Apply ELO K=32. Returns (winner_delta, loser_delta)."""
    rw, rl = get_rating(winner), get_rating(loser)
    expected_w = 1 / (1 + 10 ** ((rl - rw) / 400))
    delta = round(32 * (1 - expected_w))
    with _connect() as con:
        con.execute("UPDATE users SET rating = rating + ? WHERE username = ?", (delta, winner))
        con.execute("UPDATE users SET rating = rating - ? WHERE username = ?", (delta, loser))
    return delta, -delta
