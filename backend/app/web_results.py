"""Scrape finished World Cup scores from public web pages.

Primary target (user request): FBref World Cup pages
  - https://fbref.com/en/comps/1/World-Cup-Stats
  - https://fbref.com/en/comps/1/schedule/World-Cup-Scores-and-Fixtures

FBref is often behind Cloudflare; we try several fetch strategies, then fall back
to Wikipedia's 2026 FIFA World Cup page (same tournament, fhome/fscore/faway markup)
so leaderboard updates still work without a paid football API plan.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.team_names_en import names_match, to_english

logger = logging.getLogger("wc_fantasy.web_results")

FBREF_URLS = [
    "https://fbref.com/en/comps/1/schedule/World-Cup-Scores-and-Fixtures",
    "https://fbref.com/en/comps/1/2026/schedule/2026-World-Cup-Scores-and-Fixtures",
    "https://fbref.com/en/comps/1/World-Cup-Stats",
    "https://fbref.com/en/comps/1/World-Cup-Scores-and-Fixtures",
]

WIKI_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 WC-Fantasy-Quiniela/1.0"
)

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}


@dataclass
class ScrapedResult:
    home_en: str
    away_en: str
    home_score: int
    away_score: int
    source: str


def _norm_score_text(text: str) -> tuple[int, int] | None:
    text = (text or "").strip()
    # strip report links / penalties annotations like (4–3 pen.)
    text = re.sub(r"\([^)]*\)", "", text).strip()
    m = re.search(r"(\d+)\s*[–\-−]\s*(\d+)", text)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _clean_team(name: str) -> str:
    name = re.sub(r"\s+", " ", (name or "").strip())
    # drop wiki / fbref footnotes
    name = re.sub(r"\[\w+\]", "", name).strip()
    return name


async def _fetch_html(url: str) -> tuple[str | None, str]:
    """Return (html, method_note). Tries httpx then curl_cffi chrome impersonation."""
    try:
        async with httpx.AsyncClient(timeout=35.0, follow_redirects=True, headers=HEADERS) as client:
            r = await client.get(url)
            if r.status_code == 200 and len(r.text) > 15000 and "Just a moment" not in r.text[:500]:
                return r.text, f"httpx:{r.status_code}"
            logger.info("httpx %s -> %s len=%s", url, r.status_code, len(r.text))
    except Exception as e:
        logger.info("httpx failed %s: %s", url, e)

    try:
        from curl_cffi.requests import AsyncSession

        async with AsyncSession() as s:
            r = await s.get(url, impersonate="chrome120", timeout=40, headers=HEADERS)
            if r.status_code == 200 and len(r.text) > 15000 and "Just a moment" not in r.text[:500]:
                return r.text, f"curl_cffi:{r.status_code}"
            logger.info("curl_cffi %s -> %s len=%s", url, r.status_code, len(r.text))
    except Exception as e:
        logger.info("curl_cffi failed %s: %s", url, e)

    return None, "blocked_or_failed"


def _parse_fbref_html(html: str) -> list[ScrapedResult]:
    """Parse FBref scores_fixtures / sched tables (data-stat attributes)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        BeautifulSoup = None  # type: ignore

    out: list[ScrapedResult] = []
    if BeautifulSoup:
        soup = BeautifulSoup(html, "lxml")
        for row in soup.select("table tbody tr"):
            home_el = row.select_one('[data-stat="home_team"]')
            away_el = row.select_one('[data-stat="away_team"]')
            score_el = row.select_one('[data-stat="score"]')
            if not (home_el and away_el and score_el):
                continue
            home = _clean_team(home_el.get_text(" ", strip=True))
            away = _clean_team(away_el.get_text(" ", strip=True))
            sc = _norm_score_text(score_el.get_text(" ", strip=True))
            if not sc or not home or not away:
                continue
            # FBref shows en-dash score only when played; empty or vs = not played
            out.append(ScrapedResult(home, away, sc[0], sc[1], "fbref"))
        if out:
            return _dedupe_results(out)

    # Regex fallback on raw HTML
    for m in re.finditer(
        r'data-stat="home_team"[^>]*>.*?<a[^>]*>([^<]+)</a>.*?'
        r'data-stat="score"[^>]*>.*?(?:<a[^>]*>)?\s*(\d+)\s*[–\-]\s*(\d+)\s*(?:</a>)?.*?'
        r'data-stat="away_team"[^>]*>.*?<a[^>]*>([^<]+)</a>',
        html,
        re.S | re.I,
    ):
        out.append(
            ScrapedResult(
                _clean_team(m.group(1)),
                _clean_team(m.group(4)),
                int(m.group(2)),
                int(m.group(3)),
                "fbref",
            )
        )
    return _dedupe_results(out)


def _parse_wikipedia_html(html: str) -> list[ScrapedResult]:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    soup = BeautifulSoup(html, "lxml")
    out: list[ScrapedResult] = []
    for fhome in soup.select("th.fhome, td.fhome"):
        row = fhome.parent
        if not row:
            continue
        fscore = row.find(class_="fscore")
        faway = row.find(class_="faway")
        if not fscore or not faway:
            continue
        home = _clean_team(fhome.get_text(" ", strip=True))
        away = _clean_team(faway.get_text(" ", strip=True))
        sc = _norm_score_text(fscore.get_text(" ", strip=True))
        if not sc or not home or not away:
            continue
        out.append(ScrapedResult(home, away, sc[0], sc[1], "wikipedia"))
    return _dedupe_results(out)


def _dedupe_results(items: list[ScrapedResult]) -> list[ScrapedResult]:
    seen: set[tuple[str, str, int, int]] = set()
    out: list[ScrapedResult] = []
    for it in items:
        key = (it.home_en.lower(), it.away_en.lower(), it.home_score, it.away_score)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


async def fetch_fbref_results() -> list[ScrapedResult]:
    for url in FBREF_URLS:
        html, how = await _fetch_html(url)
        if not html:
            continue
        results = _parse_fbref_html(html)
        logger.info("FBref %s via %s -> %d scores", url, how, len(results))
        if results:
            return results
    return []


async def fetch_wikipedia_results() -> list[ScrapedResult]:
    html, how = await _fetch_html(WIKI_URL)
    if not html:
        logger.warning("Wikipedia fetch failed (%s)", how)
        return []
    results = _parse_wikipedia_html(html)
    logger.info("Wikipedia via %s -> %d scores", how, len(results))
    return results


async def fetch_all_web_results() -> list[ScrapedResult]:
    """FBref first (requested), then Wikipedia merge (fills gaps / CF blocks)."""
    by_pair: dict[tuple[str, str], ScrapedResult] = {}

    for r in await fetch_fbref_results():
        by_pair[(r.home_en.lower(), r.away_en.lower())] = r

    for r in await fetch_wikipedia_results():
        key = (r.home_en.lower(), r.away_en.lower())
        if key not in by_pair:
            by_pair[key] = r

    return list(by_pair.values())


def match_scraped_to_db_teams(
    our_home_es: str,
    our_away_es: str,
    scraped: list[ScrapedResult],
) -> tuple[int, int, str] | None:
    """Return (home_score, away_score, source) in DB team order if a scraped row matches."""
    for r in scraped:
        home_ok = names_match(our_home_es, r.home_en)
        away_ok = names_match(our_away_es, r.away_en)
        if home_ok and away_ok:
            return r.home_score, r.away_score, r.source

        # Reversed home/away on page vs our CSV order
        home_rev = names_match(our_home_es, r.away_en)
        away_rev = names_match(our_away_es, r.home_en)
        if home_rev and away_rev:
            return r.away_score, r.home_score, r.source

        # Also try English of our names directly
        eh, ea = to_english(our_home_es), to_english(our_away_es)
        if eh.lower() == r.home_en.lower() and ea.lower() == r.away_en.lower():
            return r.home_score, r.away_score, r.source
        if eh.lower() == r.away_en.lower() and ea.lower() == r.home_en.lower():
            return r.away_score, r.home_score, r.source

    return None


def web_results_status() -> dict[str, Any]:
    return {
        "fbref_urls": FBREF_URLS,
        "wikipedia_url": WIKI_URL,
        "note": "FBref may be Cloudflare-blocked; Wikipedia used as automatic fallback.",
    }
