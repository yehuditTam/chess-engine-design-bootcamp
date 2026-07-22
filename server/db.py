import hashlib
import hmac
import os
import sqlite3

_DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")
_ITERATIONS = 260_000


def _connect():
    con = sqlite3.connect(_DB_PATH)
    con.execute(
        "CREATE TABLE IF NOT EXISTS users "
        "(username TEXT PRIMARY KEY, password_hash TEXT, salt TEXT, rating INTEGER DEFAULT 1200)"
    )
    # migrate existing DB that lacks the salt column
    cols = {r[1] for r in con.execute("PRAGMA table_info(users)")}
    if "salt" not in cols:
        con.execute("ALTER TABLE users ADD COLUMN salt TEXT")
    con.commit()
    return con


def _hash(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return dk.hex()


def register(username: str, password: str) -> bool:
    """Return True on success, False if username already taken."""
    salt = os.urandom(32)
    try:
        with _connect() as con:
            con.execute(
                "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
                (username, _hash(password, salt), salt.hex()),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def authenticate(username: str, password: str) -> bool:
    with _connect() as con:
        row = con.execute(
            "SELECT password_hash, salt FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        return False
    stored_hash, salt_hex = row
    expected = _hash(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(stored_hash, expected)


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
