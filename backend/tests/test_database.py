"""Database helpers."""

from unittest.mock import MagicMock, patch

from app.database import get_db


def test_get_db_yields_and_closes():
    session = MagicMock()
    with patch("app.database.SessionLocal", return_value=session):
        gen = get_db()
        db = next(gen)
        assert db is session
        try:
            next(gen)
        except StopIteration:
            pass
    session.close.assert_called_once()
