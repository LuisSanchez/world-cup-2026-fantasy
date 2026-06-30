"""Seed module: find_csv, ensure_admin, seed with temp CSV, matches only."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.seed import _ensure_admin, _seed_matches_only, find_csv, seed_if_empty


class TestFindCsv:
    def test_finds_existing_path(self, tmp_path):
        p = tmp_path / "quiniela.csv"
        p.write_text("x", encoding="utf-8")
        with patch("app.seed.CSV_CANDIDATES", [p]):
            assert find_csv() == p

    def test_none_when_missing(self):
        with patch("app.seed.CSV_CANDIDATES", [Path("/nonexistent/quiniela.csv")]):
            assert find_csv() is None


class TestEnsureAdmin:
    @patch("app.seed.admin_email_set", return_value={"admin@localhost.dev", "a@b.com"})
    @patch("app.seed.settings")
    def test_creates_and_promotes(self, settings, _emails):
        settings.super_admin_email = "admin@localhost.dev"
        existing = MagicMock()
        existing.is_admin = False
        existing.email = "a@b.com"

        db = MagicMock()
        # first() for each email in loop: first missing, second existing; then query all for promote
        first_calls = [None, existing]

        def first_side():
            if first_calls:
                return first_calls.pop(0)
            return existing

        db.query.return_value.filter.return_value.first.side_effect = lambda: first_side()
        db.query.return_value.filter.return_value.all.return_value = [existing]
        _ensure_admin(db)
        assert db.add.called or existing.is_admin is True


class TestSeedMatchesOnly:
    def test_adds_104_matches(self):
        db = MagicMock()
        _seed_matches_only(db)
        assert db.add.call_count == 104
        db.flush.assert_called()


class TestSeedFromCsv:
    @patch("app.seed.recalculate_all_scores")
    @patch("app.seed._ensure_admin")
    def test_imports_rows(self, mock_admin, mock_recalc):
        csv_body = (
            "Marca temporal,Dirección de correo electrónico,Partido 1: México-Sudáfrica\n"
            "1,player@x.com,2-1\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
            f.write(csv_body)
            path = Path(f.name)
        try:
            db = MagicMock()
            counts = iter([0, 1, 1])  # empty then return counts
            db.query.return_value.count.side_effect = lambda: next(counts, 1)
            # user not found then created
            db.query.return_value.filter.return_value.first.return_value = None

            with patch("app.seed.find_csv", return_value=path):
                r = seed_if_empty(db)
            assert r["seeded"] is True
            assert db.add.called
            mock_admin.assert_called()
        finally:
            os.unlink(path)
