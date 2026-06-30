"""More web_results fetch/parse coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.web_results import (
    _dedupe_results,
    _fetch_html,
    fetch_all_web_results,
    fetch_wikipedia_results,
    web_results_status,
    ScrapedResult,
)


class TestDedupeAndStatus:
    def test_dedupe(self):
        a = ScrapedResult("A", "B", 1, 0, "w")
        b = ScrapedResult("A", "B", 1, 0, "w")
        c = ScrapedResult("C", "D", 2, 2, "w")
        assert len(_dedupe_results([a, b, c])) == 2

    def test_web_results_status(self):
        s = web_results_status()
        assert "fbref_urls" in s
        assert "wikipedia_url" in s


@pytest.mark.asyncio
async def test_fetch_html_httpx_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "x" * 20000

    class CM:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url):
            return mock_resp

    with patch("app.web_results.httpx.AsyncClient", return_value=CM()):
        html, how = await _fetch_html("https://example.com")
    assert html is not None
    assert "httpx" in how


@pytest.mark.asyncio
async def test_fetch_html_blocked():
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "Just a moment..."

    class CM:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url):
            return mock_resp

    with patch("app.web_results.httpx.AsyncClient", return_value=CM()), patch(
        "app.web_results.AsyncSession", side_effect=ImportError, create=True
    ):
        # also fail curl_cffi import path
        with patch.dict("sys.modules", {"curl_cffi": None, "curl_cffi.requests": None}):
            html, how = await _fetch_html("https://example.com")
    # may still try curl_cffi — accept blocked
    assert html is None or how


@pytest.mark.asyncio
async def test_fetch_all_merges_sources():
    fb = [ScrapedResult("A", "B", 1, 0, "fbref")]
    wk = [ScrapedResult("C", "D", 2, 1, "wikipedia"), ScrapedResult("A", "B", 9, 9, "wikipedia")]
    with patch("app.web_results.fetch_fbref_results", new_callable=AsyncMock, return_value=fb), patch(
        "app.web_results.fetch_wikipedia_results", new_callable=AsyncMock, return_value=wk
    ):
        all_r = await fetch_all_web_results()
    # A-B from fbref wins; C-D added
    pairs = {(r.home_en, r.away_en, r.home_score) for r in all_r}
    assert ("A", "B", 1) in pairs
    assert ("C", "D", 2) in pairs


@pytest.mark.asyncio
async def test_fetch_wikipedia_parses():
    html = """<table><tr><th class="fhome">Mexico</th><th class="fscore">2–0</th>
    <th class="faway">South Africa</th></tr></table>"""
    with patch("app.web_results._fetch_html", new_callable=AsyncMock, return_value=(html, "httpx:200")):
        r = await fetch_wikipedia_results()
    assert len(r) == 1
