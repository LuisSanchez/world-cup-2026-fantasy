"""Unit tests for web scrape parsers (HTML in memory; network mocked)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.web_results import (
    ScrapedResult,
    _norm_score_text,
    _parse_fbref_html,
    _parse_wikipedia_html,
    match_scraped_to_db_teams,
)


class TestNormScoreText:
    def test_hyphen(self):
        assert _norm_score_text("2-1") == (2, 1)

    def test_en_dash(self):
        assert _norm_score_text("3–0") == (3, 0)

    def test_strips_parens(self):
        assert _norm_score_text("1–1 (4–3 pen.)") == (1, 1)

    def test_invalid(self):
        assert _norm_score_text("vs") is None


class TestParseWikipediaHtml:
    def test_fhome_fscore_faway(self):
        html = """
        <table><tr>
          <th class="fhome">Mexico</th>
          <th class="fscore">2–0</th>
          <th class="faway">South Africa</th>
        </tr></table>
        """
        results = _parse_wikipedia_html(html)
        assert len(results) == 1
        assert results[0].home_en == "Mexico"
        assert results[0].home_score == 2
        assert results[0].away_score == 0
        assert results[0].source == "wikipedia"


class TestParseFBrefHtml:
    def test_data_stat_row(self):
        html = """
        <table><tbody><tr>
          <td data-stat="home_team"><a>Brazil</a></td>
          <td data-stat="score"><a>3–0</a></td>
          <td data-stat="away_team"><a>Haiti</a></td>
        </tr></tbody></table>
        """
        results = _parse_fbref_html(html)
        assert len(results) >= 1
        r = results[0]
        assert r.home_en == "Brazil"
        assert r.away_score == 0


class TestMatchScrapedToDb:
    def test_direct_order(self):
        scraped = [ScrapedResult("Mexico", "South Africa", 2, 0, "wikipedia")]
        hit = match_scraped_to_db_teams("México", "Sudáfrica", scraped)
        assert hit == (2, 0, "wikipedia")

    def test_reversed_order(self):
        scraped = [ScrapedResult("Türkiye", "Paraguay", 0, 1, "wikipedia")]
        hit = match_scraped_to_db_teams("Paraguay", "Turquía", scraped)
        assert hit is not None
        assert hit[0] == 1 and hit[1] == 0

    def test_no_match(self):
        scraped = [ScrapedResult("Brazil", "Haiti", 3, 0, "wikipedia")]
        assert match_scraped_to_db_teams("México", "Sudáfrica", scraped) is None


@pytest.mark.asyncio
async def test_fetch_fbref_returns_empty_when_blocked():
    from app.web_results import fetch_fbref_results

    with patch("app.web_results._fetch_html", new_callable=AsyncMock, return_value=(None, "blocked")):
        assert await fetch_fbref_results() == []
