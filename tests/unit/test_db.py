"""
Tests for server/db.py — uses a temporary file-based DB patched via monkeypatch.
"""

import pytest
from unittest.mock import patch
import tempfile
import os


def _make_db(tmp_path):
    """Returns a db module wired to a fresh temp database."""
    import importlib
    import server.db as db
    db_file = str(tmp_path / "test_users.db")
    with patch.object(db, "_DB_PATH", db_file):
        yield db


@pytest.fixture()
def db(tmp_path):
    import server.db as _db
    db_file = str(tmp_path / "test_users.db")
    with patch.object(_db, "_DB_PATH", db_file):
        yield _db


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_new_user_returns_true(self, db):
        assert db.register("alice", "pass123") is True

    def test_register_duplicate_returns_false(self, db):
        db.register("alice", "pass123")
        assert db.register("alice", "other") is False

    def test_register_different_users_both_succeed(self, db):
        assert db.register("alice", "a") is True
        assert db.register("bob", "b") is True

    def test_registered_user_has_default_rating(self, db):
        db.register("alice", "pass")
        assert db.get_rating("alice") == 1200


# ---------------------------------------------------------------------------
# authenticate
# ---------------------------------------------------------------------------

class TestAuthenticate:
    def test_correct_password_returns_true(self, db):
        db.register("alice", "secret")
        assert db.authenticate("alice", "secret") is True

    def test_wrong_password_returns_false(self, db):
        db.register("alice", "secret")
        assert db.authenticate("alice", "wrong") is False

    def test_unknown_user_returns_false(self, db):
        assert db.authenticate("nobody", "pass") is False

    def test_password_is_hashed_not_plaintext(self, db):
        db.register("alice", "mypassword")
        import sqlite3
        import server.db as raw_db
        with patch.object(raw_db, "_DB_PATH", db._DB_PATH):
            con = sqlite3.connect(db._DB_PATH)
            row = con.execute(
                "SELECT password_hash FROM users WHERE username = ?", ("alice",)
            ).fetchone()
            con.close()
        assert row[0] != "mypassword"
        assert len(row[0]) == 64  # SHA-256 hex digest


# ---------------------------------------------------------------------------
# get_rating
# ---------------------------------------------------------------------------

class TestGetRating:
    def test_default_rating_is_1200(self, db):
        db.register("alice", "pass")
        assert db.get_rating("alice") == 1200

    def test_unknown_user_returns_1200(self, db):
        assert db.get_rating("ghost") == 1200


# ---------------------------------------------------------------------------
# update_ratings (ELO)
# ---------------------------------------------------------------------------

class TestUpdateRatings:
    def test_winner_gains_points(self, db):
        db.register("alice", "a")
        db.register("bob", "b")
        w_delta, _ = db.update_ratings("alice", "bob")
        assert w_delta > 0
        assert db.get_rating("alice") > 1200

    def test_loser_loses_points(self, db):
        db.register("alice", "a")
        db.register("bob", "b")
        _, l_delta = db.update_ratings("alice", "bob")
        assert l_delta < 0
        assert db.get_rating("bob") < 1200

    def test_deltas_are_equal_and_opposite(self, db):
        db.register("alice", "a")
        db.register("bob", "b")
        w_delta, l_delta = db.update_ratings("alice", "bob")
        assert w_delta == -l_delta

    def test_equal_ratings_delta_is_16(self, db):
        """With equal ratings, expected score = 0.5, so delta = round(32 * 0.5) = 16."""
        db.register("alice", "a")
        db.register("bob", "b")
        w_delta, _ = db.update_ratings("alice", "bob")
        assert w_delta == 16

    def test_higher_rated_winner_gains_less(self, db):
        """A strong player beating a weak one should gain fewer points than 16."""
        import sqlite3
        db.register("strong", "a")
        db.register("weak", "b")
        # Manually set strong=1600, weak=1200
        con = sqlite3.connect(db._DB_PATH)
        con.execute("UPDATE users SET rating = 1600 WHERE username = 'strong'")
        con.execute("UPDATE users SET rating = 1200 WHERE username = 'weak'")
        con.commit()
        con.close()
        w_delta, _ = db.update_ratings("strong", "weak")
        assert w_delta < 16

    def test_ratings_sum_is_conserved(self, db):
        db.register("alice", "a")
        db.register("bob", "b")
        db.update_ratings("alice", "bob")
        total = db.get_rating("alice") + db.get_rating("bob")
        assert total == 2400
