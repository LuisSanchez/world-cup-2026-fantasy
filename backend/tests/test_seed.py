"""Unit tests for seed helpers (no real DB / filesystem when mocked)."""

from unittest.mock import MagicMock, mock_open, patch

from app.seed import parse_match_header, parse_score, seed_if_empty


class TestParseScore:
    def test_standard(self):
        assert parse_score("2-1") == (2, 1)

    def test_en_dash(self):
        assert parse_score("3–0") == (3, 0)

    def test_spaces(self):
        assert parse_score(" 1 - 1 ") == (1, 1)

    def test_empty(self):
        assert parse_score("") is None
        assert parse_score("   ") is None

    def test_invalid(self):
        assert parse_score("abc") is None


class TestParseMatchHeader:
    def test_normal(self):
        num, home, away, ph = parse_match_header("Partido 1: México-Sudáfrica")
        assert num == 1
        assert home == "México"
        assert away == "Sudáfrica"
        assert ph is False

    def test_placeholder(self):
        num, home, away, ph = parse_match_header("Partido 73: 16vos Por Definir")
        assert num == 73
        assert ph is True

    def test_invalid(self):
        num, _, _, _ = parse_match_header("not a match")
        assert num == 0


class TestSeedIfEmpty:
    def test_skips_when_matches_exist(self):
        db = MagicMock()
        q = MagicMock()
        db.query.return_value = q
        q.count.return_value = 10

        r = seed_if_empty(db)
        assert r["seeded"] is False
        assert r["matches"] == 10

    @patch("app.seed.find_csv", return_value=None)
    @patch("app.seed._seed_matches_only")
    @patch("app.seed._ensure_admin")
    def test_seeds_matches_only_without_csv(self, mock_admin, mock_seed_m, mock_csv):
        db = MagicMock()
        # first count = 0 (empty), later counts for return
        counts = iter([0, 104, 1])
        db.query.return_value.count.side_effect = lambda: next(counts, 0)

        r = seed_if_empty(db)
        assert r["seeded"] is True
        mock_seed_m.assert_called_once_with(db)
        mock_admin.assert_called_once_with(db)
