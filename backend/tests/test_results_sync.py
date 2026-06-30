"""Unit tests for results_sync helpers with mocks."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.results_sync import (
    _fixture_finished_score,
    _needs_score_fetch,
    apply_score_to_match,
)


class TestFixtureFinishedScore:
    def test_ft(self):
        item = {"fixture": {"status": {"short": "FT"}}, "goals": {"home": 2, "away": 1}}
        assert _fixture_finished_score(item) == (2, 1)

    def test_live_not_finished(self):
        item = {"fixture": {"status": {"short": "1H"}}, "goals": {"home": 1, "away": 0}}
        assert _fixture_finished_score(item) is None

    def test_pen_allowed(self):
        item = {"fixture": {"status": {"short": "PEN"}}, "goals": {"home": 1, "away": 1}}
        assert _fixture_finished_score(item) == (1, 1)


class TestNeedsScoreFetch:
    def test_before_end_false(self):
        m = SimpleNamespace(
            is_finished=False,
            home_score=None,
            away_score=None,
            is_placeholder=False,
            home_team="México",
            kickoff=datetime.utcnow() - timedelta(minutes=30),
        )
        assert _needs_score_fetch(m, datetime.utcnow(), 110, 5) is False

    def test_after_end_true(self):
        m = SimpleNamespace(
            is_finished=False,
            home_score=None,
            away_score=None,
            is_placeholder=False,
            home_team="México",
            kickoff=datetime.utcnow() - timedelta(minutes=120),
        )
        assert _needs_score_fetch(m, datetime.utcnow(), 110, 5) is True

    def test_already_finished_false(self):
        m = SimpleNamespace(
            is_finished=True,
            home_score=1,
            away_score=0,
            is_placeholder=False,
            home_team="México",
            kickoff=datetime.utcnow() - timedelta(hours=3),
        )
        assert _needs_score_fetch(m, datetime.utcnow(), 110, 5) is False


class TestApplyScoreToMatch:
    @patch("app.results_sync.recalculate_match_predictions")
    def test_applies_and_returns_true(self, mock_recalc):
        match = SimpleNamespace(
            match_number=1,
            home_team="A",
            away_team="B",
            home_score=None,
            away_score=None,
            is_finished=False,
        )
        db = MagicMock()
        assert apply_score_to_match(db, match, 2, 1, "test") is True
        assert match.home_score == 2
        assert match.is_finished is True
        mock_recalc.assert_called_once()

    @patch("app.results_sync.recalculate_match_predictions")
    def test_no_change_returns_false(self, mock_recalc):
        match = SimpleNamespace(
            match_number=1,
            home_team="A",
            away_team="B",
            home_score=2,
            away_score=1,
            is_finished=True,
        )
        assert apply_score_to_match(MagicMock(), match, 2, 1, "test") is False
        mock_recalc.assert_not_called()


@pytest.mark.asyncio
async def test_sync_finished_scores_no_api_key_skips_api():
    from app.results_sync import sync_finished_scores

    db = MagicMock()
    match = SimpleNamespace(
        id=1,
        match_number=1,
        home_team="México",
        away_team="Sudáfrica",
        is_finished=False,
        home_score=None,
        away_score=None,
        is_placeholder=False,
        kickoff=datetime.utcnow() - timedelta(hours=3),
    )
    # order_by().all() for all_matches; various query chains
    db.query.return_value.order_by.return_value.all.return_value = [match]
    db.query.return_value.filter.return_value.all.return_value = [match]

    with patch("app.results_sync.get_settings") as gs, patch(
        "app.results_sync.fetch_all_web_results", return_value=[]
    ) as web, patch("app.results_sync._fetch_wc_fixtures") as api:
        gs.return_value = SimpleNamespace(
            football_api_key="",
            match_duration_minutes=110,
            results_fetch_window_minutes=5,
        )
        r = await sync_finished_scores(db, force_all=True)

    web.assert_awaited()
    api.assert_not_called()
    assert r["skipped_no_api_key"] is True
