"""Auto-fetch finished match scores from external API and update leaderboard.

Strategy:
- Background loop runs every `results_poll_seconds` (default 60s).
- Also invokable from API routes (throttled) so scores refresh even without relying only on the loop.
- For each unfinished match whose kickoff + match_duration has passed (and within
  `results_fetch_window_minutes` after expected end, or any time after if still missing score),
  try to resolve the final score via API-Football (league 1 = World Cup, season 2026).
- On success: set home/away score, is_finished=True, recalculate predictions + leaderboard.

Requires FOOTBALL_API_KEY (api-sports.io / api-football.com). Without a key, the worker
logs and skips external calls; admin can still set scores manually.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models import Match
from app.scoring import recalculate_match_predictions
from app.team_names_en import names_match
from app.web_results import fetch_all_web_results, match_scraped_to_db_teams

logger = logging.getLogger("wc_fantasy.results_sync")

API_BASE = "https://v3.football.api-sports.io"

# In-memory throttle for on-request sync (avoid spamming API from every page load)
_last_request_sync: datetime | None = None
_last_full_fetch: datetime | None = None
_fixture_cache: list[dict[str, Any]] = []
_cache_fetched_at: datetime | None = None

_bg_task: asyncio.Task | None = None
_stop_event: asyncio.Event | None = None

# Runtime override for cron jobs. None = use Settings.cron_jobs_enabled (default False).
_runtime_cron_enabled: bool | None = None


def is_cron_jobs_enabled() -> bool:
    """Whether background + on-request maintenance jobs may run."""
    if _runtime_cron_enabled is not None:
        return _runtime_cron_enabled
    return bool(get_settings().cron_jobs_enabled)


def background_worker_running() -> bool:
    return _bg_task is not None and not _bg_task.done()


def get_cron_jobs_status() -> dict[str, Any]:
    settings = get_settings()
    return {
        "cron_jobs_enabled": is_cron_jobs_enabled(),
        "cron_jobs_env_default": bool(settings.cron_jobs_enabled),
        "runtime_override": _runtime_cron_enabled,
        "background_worker_running": background_worker_running(),
        "results_poll_seconds": settings.results_poll_seconds,
        "results_request_throttle_seconds": settings.results_request_throttle_seconds,
    }


async def set_cron_jobs_enabled(enabled: bool) -> dict[str, Any]:
    """Enable/disable all automatic jobs; start or stop the background worker."""
    global _runtime_cron_enabled
    enabled = bool(enabled)
    _runtime_cron_enabled = enabled
    if enabled:
        start_background_sync()
        logger.info("Cron jobs ENABLED (background worker + on-request sync)")
    else:
        await stop_background_sync()
        logger.info("Cron jobs DISABLED (background worker + on-request sync stopped)")
    return get_cron_jobs_status()


def _expected_end(match: Match, duration_min: int) -> datetime | None:
    if not match.kickoff:
        return None
    return match.kickoff + timedelta(minutes=duration_min)


def _needs_score_fetch(match: Match, now: datetime, duration_min: int, window_min: int) -> bool:
    """Match is past expected end, not yet finished in DB, and worth polling."""
    if match.is_finished and match.home_score is not None and match.away_score is not None:
        return False
    if match.is_placeholder and "Por Definir" in (match.home_team or ""):
        return False
    end = _expected_end(match, duration_min)
    if not end:
        return False
    if now < end:
        return False
    # Prefer fetching within the window; also retry later if still no score (catch late results)
    if now <= end + timedelta(minutes=window_min):
        return True
    # Outside window but still missing official score — retry less aggressively handled by poll interval
    if match.home_score is None or match.away_score is None:
        return True
    return False


async def _fetch_wc_fixtures(api_key: str) -> list[dict[str, Any]]:
    """Fetch fixtures for matching.

    Free API-Football plans often block `league=1&season=2026` but allow `/fixtures?date=YYYY-MM-DD`
    for a narrow recent window, and `live=all`. We try season query first, then fall back to
    date-range (+ live) and filter to World Cup (league id 1) when present, else keep all for
    team-name matching.
    """
    global _fixture_cache, _cache_fetched_at
    settings = get_settings()
    now = datetime.utcnow()
    ttl = settings.results_cache_seconds
    if _fixture_cache and _cache_fetched_at and (now - _cache_fetched_at).total_seconds() < ttl:
        return _fixture_cache

    headers = {"x-apisports-key": api_key}
    league_id = settings.football_league_id
    season = settings.football_season
    collected: dict[int, dict[str, Any]] = {}

    def _ingest(items: list[dict[str, Any]], prefer_league: bool = True) -> None:
        for it in items or []:
            fid = (it.get("fixture") or {}).get("id")
            if not fid:
                continue
            lid = (it.get("league") or {}).get("id")
            if prefer_league and lid != league_id:
                # still store non-WC as fallback for team match if nothing else
                if fid not in collected:
                    collected[fid] = it
            else:
                collected[fid] = it

    async with httpx.AsyncClient(timeout=40.0, base_url=API_BASE) as client:
        # 1) Preferred: full season (works on paid / higher plans)
        res = await client.get(
            "/fixtures",
            headers=headers,
            params={"league": str(league_id), "season": str(season)},
        )
        if res.status_code == 200:
            data = res.json()
            errs = data.get("errors")
            resp = data.get("response") or []
            if errs:
                logger.warning("Football API season query errors: %s — falling back to date/live", errs)
            if resp:
                _ingest(resp, prefer_league=False)
                logger.info("Fetched %d fixtures via league/season", len(resp))

        # 2) Live fixtures (any league; team match later)
        try:
            res_live = await client.get("/fixtures", headers=headers, params={"live": "all"})
            if res_live.status_code == 200:
                live_resp = res_live.json().get("response") or []
                _ingest(live_resp, prefer_league=False)
                logger.info("Fetched %d live fixtures", len(live_resp))
        except Exception as e:
            logger.warning("Live fixtures fetch failed: %s", e)

        # 3) Date window around today (free tier often only allows ~today ±1 day)
        span = max(0, settings.results_date_span_days)
        for delta in range(-span, span + 1):
            day = (now + timedelta(days=delta)).date().isoformat()
            try:
                res_d = await client.get("/fixtures", headers=headers, params={"date": day})
                if res_d.status_code != 200:
                    continue
                data_d = res_d.json()
                if data_d.get("errors"):
                    logger.debug("Date %s errors: %s", day, data_d.get("errors"))
                    continue
                resp_d = data_d.get("response") or []
                wc = [x for x in resp_d if (x.get("league") or {}).get("id") == league_id]
                _ingest(wc if wc else resp_d, prefer_league=False)
                logger.info("Fetched date %s: total=%d wc=%d", day, len(resp_d), len(wc))
            except Exception as e:
                logger.warning("Date %s fetch failed: %s", day, e)
            await asyncio.sleep(0.25)

        # 4) Kickoff dates for unfinished DB matches (best-effort within plan limits)
        try:
            db_tmp = SessionLocal()
            try:
                pending = (
                    db_tmp.query(Match)
                    .filter(
                        (Match.is_finished == False)  # noqa: E712
                        | (Match.home_score.is_(None))
                    )
                    .all()
                )
                days_needed: set[str] = set()
                for m in pending:
                    if m.kickoff:
                        days_needed.add(m.kickoff.date().isoformat())
                # limit extra requests
                for day in sorted(days_needed)[:14]:
                    if any(
                        abs((datetime.fromisoformat(day) - now).days) <= span
                        for _ in [1]
                    ):
                        continue  # already fetched in span
                    res_d = await client.get("/fixtures", headers=headers, params={"date": day})
                    if res_d.status_code != 200:
                        continue
                    data_d = res_d.json()
                    if data_d.get("errors"):
                        continue
                    resp_d = data_d.get("response") or []
                    wc = [x for x in resp_d if (x.get("league") or {}).get("id") == league_id]
                    _ingest(wc if wc else resp_d, prefer_league=False)
                    await asyncio.sleep(0.25)
            finally:
                db_tmp.close()
        except Exception as e:
            logger.warning("Kickoff-date fetch skipped: %s", e)

    _fixture_cache = list(collected.values())
    _cache_fetched_at = now
    logger.info("Fixture cache size: %d", len(_fixture_cache))
    return _fixture_cache


def _fixture_finished_score(item: dict[str, Any]) -> tuple[int, int] | None:
    """Return (home, away) if fixture is finished with scores, else None."""
    fixture = item.get("fixture") or {}
    status = (fixture.get("status") or {}).get("short") or ""
    # FT = full time, AET = after extra time, PEN = penalties (use FT goals, not pen shootout)
    if status not in ("FT", "AET", "PEN"):
        return None
    goals = item.get("goals") or {}
    home = goals.get("home")
    away = goals.get("away")
    if home is None or away is None:
        return None
    return int(home), int(away)


def _fixture_teams(item: dict[str, Any]) -> tuple[str, str]:
    teams = item.get("teams") or {}
    home = (teams.get("home") or {}).get("name") or ""
    away = (teams.get("away") or {}).get("name") or ""
    return home, away


def _match_fixture_to_db(match: Match, fixtures: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Find best fixture for our Match by team names; prefer kickoff date proximity."""
    candidates: list[tuple[float, dict[str, Any]]] = []
    for item in fixtures:
        api_home, api_away = _fixture_teams(item)
        if not api_home or not api_away:
            continue
        home_ok = names_match(match.home_team, api_home)
        away_ok = names_match(match.away_team, api_away)
        # Also try reversed in case order differs (shouldn't for group, possible in some feeds)
        home_rev = names_match(match.home_team, api_away)
        away_rev = names_match(match.away_team, api_home)
        if not ((home_ok and away_ok) or (home_rev and away_rev)):
            continue
        score_penalty = 0.0
        if match.kickoff:
            fix_date = (item.get("fixture") or {}).get("date")
            if fix_date:
                try:
                    # e.g. 2026-06-11T19:00:00+00:00
                    fix_dt = datetime.fromisoformat(fix_date.replace("Z", "+00:00")).replace(tzinfo=None)
                    score_penalty = abs((fix_dt - match.kickoff).total_seconds()) / 3600.0
                except ValueError:
                    pass
        candidates.append((score_penalty, item))

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _parse_fixture_kickoff_utc(item: dict[str, Any]) -> datetime | None:
    fix_date = (item.get("fixture") or {}).get("date")
    if not fix_date:
        return None
    try:
        return datetime.fromisoformat(fix_date.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


_LIVE_STATUSES = frozenset(
    {"1H", "2H", "HT", "ET", "BT", "P", "LIVE", "INT", "SUSP"}
)


def apply_fixture_kickoff(match: Match, item: dict[str, Any]) -> bool:
    """Update stored kickoff from API fixture (fixes approximate seed schedule)."""
    ko = _parse_fixture_kickoff_utc(item)
    if not ko:
        return False
    status = ((item.get("fixture") or {}).get("status") or {}).get("short") or ""
    # If API says live but our kickoff is still in the future, force kickoff into the past
    if status in _LIVE_STATUSES and (not match.kickoff or match.kickoff > datetime.utcnow()):
        # 45' into game ≈ kickoff 45 min ago when we only have status not elapsed
        elapsed = ((item.get("fixture") or {}).get("status") or {}).get("elapsed")
        mins = int(elapsed) if isinstance(elapsed, int) else 45
        ko = datetime.utcnow() - timedelta(minutes=max(mins, 1))
    if match.kickoff == ko:
        return False
    match.kickoff = ko
    logger.info(
        "Kickoff updated match #%s %s-%s -> %s (api status=%s)",
        match.match_number,
        match.home_team,
        match.away_team,
        ko.isoformat(),
        status,
    )
    return True


def apply_score_to_match(db: Session, match: Match, home: int, away: int, source: str) -> bool:
    """Persist score + recalculate. Returns True if something changed."""
    changed = (
        match.home_score != home
        or match.away_score != away
        or not match.is_finished
    )
    if not changed:
        return False
    match.home_score = home
    match.away_score = away
    match.is_finished = True
    recalculate_match_predictions(db, match)
    logger.info(
        "Auto-updated match #%s %s-%s -> %s-%s (source=%s)",
        match.match_number,
        match.home_team,
        match.away_team,
        home,
        away,
        source,
    )
    return True


async def sync_finished_scores(
    db: Session | None = None,
    *,
    force_all: bool = False,
) -> dict[str, Any]:
    """Main entry: poll external API and update any eligible matches.

    force_all=True: try every unfinished non-placeholder match (admin / one-off), not only
    those past expected end time.
    """
    settings = get_settings()
    own_session = db is None
    if own_session:
        db = SessionLocal()

    result: dict[str, Any] = {
        "checked": 0,
        "updated": 0,
        "skipped_no_api_key": False,
        "skipped_no_fixtures": False,
        "web_results_count": 0,
        "api_fixtures_count": 0,
        "errors": [],
        "updates": [],
        "not_finished_yet": 0,
        "no_fixture_match": 0,
        "sources_used": [],
    }

    try:
        now = datetime.utcnow()
        duration = settings.match_duration_minutes
        window = settings.results_fetch_window_minutes

        all_matches = db.query(Match).order_by(Match.match_number).all()
        if force_all:
            to_fetch = [
                m
                for m in all_matches
                if not (
                    m.is_finished
                    and m.home_score is not None
                    and m.away_score is not None
                )
                and not (m.is_placeholder and "Por Definir" in (m.home_team or ""))
            ]
        else:
            to_fetch = [m for m in all_matches if _needs_score_fetch(m, now, duration, window)]
        result["checked"] = len(to_fetch)
        result["kickoffs_updated"] = 0

        # ── 1) Web scrape: FBref (preferred) + Wikipedia fallback ──
        web_results = []
        try:
            web_results = await fetch_all_web_results()
            result["web_results_count"] = len(web_results)
            if web_results:
                result["sources_used"].append("web")
        except Exception as e:
            result["errors"].append(f"web:{e}")
            logger.exception("Web results fetch failed")

        # ── 2) API-Football (optional; often limited on free tier for WC 2026) ──
        fixtures: list[dict[str, Any]] = []
        api_key = (settings.football_api_key or "").strip()
        if api_key:
            try:
                fixtures = await _fetch_wc_fixtures(api_key)
                result["api_fixtures_count"] = len(fixtures)
                if fixtures:
                    result["sources_used"].append("api-football")
            except Exception as e:
                result["errors"].append(f"api:{e}")
                logger.exception("Fixture fetch error")
        else:
            result["skipped_no_api_key"] = True

        # Always try to correct kickoffs from API for unfinished matches (fixes wrong countdown)
        if fixtures:
            for m in all_matches:
                if m.is_finished and m.home_score is not None:
                    continue
                if m.is_placeholder and "Por Definir" in (m.home_team or ""):
                    continue
                item = _match_fixture_to_db(m, fixtures)
                if item and apply_fixture_kickoff(m, item):
                    result["kickoffs_updated"] += 1
            if result["kickoffs_updated"]:
                db.commit()

        if not to_fetch:
            return result

        if not web_results and not fixtures:
            result["skipped_no_fixtures"] = True
            return result

        for match in to_fetch:
            home: int | None = None
            away: int | None = None
            source = ""

            # Prefer web scrape (more complete for WC 2026 on free plans)
            if web_results:
                hit = match_scraped_to_db_teams(match.home_team, match.away_team, web_results)
                if hit:
                    home, away, source = hit

            # Fall back to API-Football
            if home is None and fixtures:
                item = _match_fixture_to_db(match, fixtures)
                if item:
                    apply_fixture_kickoff(match, item)  # keep kickoff current even mid-match
                    score = _fixture_finished_score(item)
                    if score:
                        home, away = score
                        source = "api-football"
                        api_home, api_away = _fixture_teams(item)
                        if names_match(match.home_team, api_away) and names_match(
                            match.away_team, api_home
                        ):
                            home, away = away, home
                    else:
                        result["not_finished_yet"] += 1
                else:
                    result["no_fixture_match"] += 1
            elif home is None:
                result["no_fixture_match"] += 1

            if home is None or away is None:
                continue

            if apply_score_to_match(db, match, home, away, source):
                result["updated"] += 1
                result["updates"].append(
                    {
                        "match_id": match.id,
                        "match_number": match.match_number,
                        "home_team": match.home_team,
                        "away_team": match.away_team,
                        "score": f"{home}-{away}",
                        "source": source,
                    }
                )

        if result["updated"]:
            db.commit()
        return result
    except Exception as e:
        result["errors"].append(str(e))
        logger.exception("sync_finished_scores failed")
        if own_session and db:
            db.rollback()
        return result
    finally:
        if own_session and db:
            db.close()


async def maybe_sync_on_request(db: Session | None = None) -> dict[str, Any] | None:
    """Throttled sync for use from read endpoints (leaderboard / matches).

    No-op when cron jobs are disabled (default). Admin force-sync still works.
    """
    if not is_cron_jobs_enabled():
        return None
    global _last_request_sync
    settings = get_settings()
    now = datetime.utcnow()
    min_interval = settings.results_request_throttle_seconds
    if _last_request_sync and (now - _last_request_sync).total_seconds() < min_interval:
        return None
    _last_request_sync = now
    return await sync_finished_scores(db)


async def _background_loop():
    settings = get_settings()
    interval = max(30, settings.results_poll_seconds)
    logger.info("Results sync background worker started (interval=%ss)", interval)
    while _stop_event and not _stop_event.is_set():
        if not is_cron_jobs_enabled():
            logger.info("Background worker idle — cron jobs disabled")
            try:
                await asyncio.wait_for(_stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
            continue
        try:
            r = await sync_finished_scores()
            if r.get("updated"):
                logger.info("Background sync updated %s match(es): %s", r["updated"], r.get("updates"))
        except Exception:
            logger.exception("Background sync tick failed")
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
    logger.info("Results sync background worker stopped")


def start_background_sync() -> None:
    """Start the poll loop only when cron jobs are enabled."""
    global _bg_task, _stop_event
    if not is_cron_jobs_enabled():
        logger.info(
            "Background results sync not started (cron jobs disabled; set CRON_JOBS_ENABLED=true "
            "or enable via Admin → Cron jobs)"
        )
        return
    if _bg_task and not _bg_task.done():
        return
    _stop_event = asyncio.Event()
    _bg_task = asyncio.create_task(_background_loop())


async def stop_background_sync() -> None:
    global _bg_task, _stop_event
    if _stop_event:
        _stop_event.set()
    if _bg_task:
        try:
            await asyncio.wait_for(_bg_task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            _bg_task.cancel()
        _bg_task = None
    _stop_event = None
