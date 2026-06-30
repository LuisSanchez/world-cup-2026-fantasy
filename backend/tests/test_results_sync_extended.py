"""Extended results_sync: matching, fetch, maybe_sync, background helpers."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.results_sync import (
    _fixture_teams,
    _match_fixture_to_db,
    maybe_sync_on_request,
    start_background_sync,
    stop_background_sync,
    sync_finished_scores,
)


class TestFixtureTeamsAndMatch:
    def test_fixture_teams(self):
        item = {"teams": {"home": {"name": "Brazil"}, "away": {"name": "Haiti"}}}
        assert _fixture_teams(item) == ("Brazil", "Haiti")

    def test_match_fixture_prefers_closer_kickoff(self):
        match = SimpleNamespace(
            home_team="Brasil",
            away_team="Haití",
            kickoff=datetime(2026, 6, 20, 19, 0, 0),
        )
        fx = [
            {
                "fixture": {"date": "2026-06-20T19:00:00+00:00", "status": {"short": "FT"}},
                "teams": {"home": {"name": "Brazil"}, "away": {"name": "Haiti"}},
                "goals": {"home": 3, "away": 0},
            }
        ]
        hit = _match_fixture_to_db(match, fx)
        assert hit is not None


class TestSyncWithWebResults:
    @pytest.mark.asyncio
    async def test_updates_from_web_scrape(self):
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
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = [match]

        from app.web_results import ScrapedResult

        web = [ScrapedResult("Mexico", "South Africa", 2, 0, "wikipedia")]

        with patch("app.results_sync.get_settings") as gs, patch(
            "app.results_sync.fetch_all_web_results", new_callable=AsyncMock, return_value=web
        ), patch("app.results_sync._fetch_wc_fixtures", new_callable=AsyncMock, return_value=[]), patch(
            "app.results_sync.recalculate_match_predictions"
        ):
            gs.return_value = SimpleNamespace(
                football_api_key="k",
                match_duration_minutes=110,
                results_fetch_window_minutes=5,
            )
            r = await sync_finished_scores(db, force_all=True)

        assert r["updated"] == 1
        assert match.home_score == 2
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_api_fallback_ft_score(self):
        match = SimpleNamespace(
            id=1,
            match_number=31,
            home_team="Brasil",
            away_team="Haití",
            is_finished=False,
            home_score=None,
            away_score=None,
            is_placeholder=False,
            kickoff=datetime.utcnow() - timedelta(hours=3),
        )
        db = MagicMock()
        db.query.return_value.order_by.return_value.all.return_value = [match]
        fixtures = [
            {
                "fixture": {"date": "2026-06-20T19:00:00+00:00", "status": {"short": "FT"}},
                "teams": {"home": {"name": "Brazil"}, "away": {"name": "Haiti"}},
                "goals": {"home": 3, "away": 0},
            }
        ]
        with patch("app.results_sync.get_settings") as gs, patch(
            "app.results_sync.fetch_all_web_results", new_callable=AsyncMock, return_value=[]
        ), patch(
            "app.results_sync._fetch_wc_fixtures", new_callable=AsyncMock, return_value=fixtures
        ), patch("app.results_sync.recalculate_match_predictions"):
            gs.return_value = SimpleNamespace(
                football_api_key="k",
                match_duration_minutes=110,
                results_fetch_window_minutes=5,
            )
            r = await sync_finished_scores(db, force_all=True)
        assert r["updated"] == 1
        assert match.away_score == 0


class TestMaybeSyncThrottle:
    @pytest.mark.asyncio
    async def test_throttle_skips_second_call(self):
        import app.results_sync as rs

        rs._last_request_sync = None
        with patch("app.results_sync.get_settings") as gs, patch(
            "app.results_sync.sync_finished_scores", new_callable=AsyncMock, return_value={"ok": 1}
        ) as sync:
            gs.return_value = SimpleNamespace(results_request_throttle_seconds=9999)
            r1 = await maybe_sync_on_request()
            r2 = await maybe_sync_on_request()
        assert r1 == {"ok": 1}
        assert r2 is None
        assert sync.await_count == 1


class TestBackgroundLifecycle:
    @pytest.mark.asyncio
    async def test_start_and_stop(self):
        import app.results_sync as rs

        rs._bg_task = None
        rs._stop_event = None
        with patch("app.results_sync.sync_finished_scores", new_callable=AsyncMock, return_value={}):
            start_background_sync()
            assert rs._bg_task is not None
            await stop_background_sync()
        assert rs._bg_task is None


@pytest.mark.asyncio
async def test_fetch_wc_fixtures_uses_cache():
    import app.results_sync as rs
    from app.results_sync import _fetch_wc_fixtures

    rs._fixture_cache = [{"id": 1}]
    rs._cache_fetched_at = datetime.utcnow()
    with patch("app.results_sync.get_settings") as gs:
        gs.return_value = SimpleNamespace(results_cache_seconds=999, football_league_id=1, football_season=2026)
        out = await _fetch_wc_fixtures("key")
    assert out == [{"id": 1}]
