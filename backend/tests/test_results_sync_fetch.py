"""Cover _fetch_wc_fixtures HTTP paths with mocked httpx."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.results_sync as rs
from app.results_sync import _fetch_wc_fixtures, _needs_score_fetch


@pytest.mark.asyncio
async def test_fetch_wc_fixtures_full_path():
    rs._fixture_cache = []
    rs._cache_fetched_at = None

    season_resp = MagicMock()
    season_resp.status_code = 200
    season_resp.json.return_value = {
        "errors": {"plan": "limited"},
        "response": [],
    }
    live_resp = MagicMock()
    live_resp.status_code = 200
    live_resp.json.return_value = {
        "response": [
            {
                "fixture": {"id": 1},
                "league": {"id": 1},
                "teams": {"home": {"name": "A"}, "away": {"name": "B"}},
            }
        ]
    }
    date_resp = MagicMock()
    date_resp.status_code = 200
    date_resp.json.return_value = {
        "response": [
            {
                "fixture": {"id": 2},
                "league": {"id": 1},
                "teams": {"home": {"name": "C"}, "away": {"name": "D"}},
            }
        ]
    }

    class ClientCM:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, path, headers=None, params=None):
            if params and params.get("season"):
                return season_resp
            if params and params.get("live"):
                return live_resp
            return date_resp

    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.all.return_value = []
    mock_db_session.close = MagicMock()

    with patch("app.results_sync.get_settings") as gs, patch(
        "app.results_sync.httpx.AsyncClient", return_value=ClientCM()
    ), patch("app.results_sync.SessionLocal", return_value=mock_db_session), patch(
        "app.results_sync.asyncio.sleep", new_callable=AsyncMock
    ):
        gs.return_value = SimpleNamespace(
            results_cache_seconds=0,
            football_league_id=1,
            football_season=2026,
            results_date_span_days=0,
        )
        out = await _fetch_wc_fixtures("apikey")
    assert len(out) >= 1


def test_needs_score_placeholder_skip():
    m = SimpleNamespace(
        is_finished=False,
        home_score=None,
        away_score=None,
        is_placeholder=True,
        home_team="16vos Por Definir",
        kickoff=datetime.utcnow(),
    )
    assert _needs_score_fetch(m, datetime.utcnow(), 110, 5) is False
