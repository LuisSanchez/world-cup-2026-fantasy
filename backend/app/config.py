from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Search .env in common locations (backend CWD, backend/.env, repo root .env)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
_ENV_FILES = tuple(
    str(p)
    for p in (
        _BACKEND_DIR / ".env",
        _REPO_ROOT / ".env",
        Path(".env"),
    )
    if p.is_file()
) or (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        # OS env vars always win over .env (important for Docker / hosting)
        env_ignore_empty=True,
    )

    app_name: str = "WC Fantasy 2026"
    secret_key: str = "dev-secret-change-in-production"
    database_url: str = "sqlite:////app/data/wc_fantasy.db"
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    google_client_id: str = ""
    google_client_secret: str = ""
    # Local/dev super admin (always admin in addition to ADMIN_EMAILS)
    super_admin_email: str = "admin@localhost.dev"
    # Comma-separated admin emails (always admin in all environments)
    admin_emails: str = ""
    # Lock predictions this many minutes before kickoff
    prediction_lock_minutes: int = 10
    # Approximate match duration for live/finished status (90+stoppage+buffer)
    match_duration_minutes: int = 110
    # Auto results: prioritize fetch within this many minutes after expected end
    results_fetch_window_minutes: int = 5
    # Background worker poll interval
    results_poll_seconds: int = 60
    # Throttle for sync triggered by normal API reads
    results_request_throttle_seconds: int = 45
    # Cache fixture list from external API
    results_cache_seconds: int = 90
    # Days before/after UTC today to query /fixtures?date= (free tier often limits to ~±1 day)
    results_date_span_days: int = 1
    # API-Football (api-sports.io) — key required for auto scores
    # Base URL: https://v3.football.api-sports.io
    football_api_key: str = ""
    football_league_id: int = 1  # World Cup
    football_season: int = 2026


@lru_cache
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Call in tests if you mutate DATABASE_URL / env after first load."""
    get_settings.cache_clear()


def admin_email_set() -> set[str]:
    """Emails that must always have is_admin=True (all environments)."""
    s = get_settings()
    emails = {s.super_admin_email.lower().strip()}
    for part in (s.admin_emails or "").split(","):
        e = part.strip().lower()
        if e:
            emails.add(e)
    return emails


def is_admin_email(email: str) -> bool:
    return email.lower().strip() in admin_email_set()


def is_leaderboard_excluded_email(email: str) -> bool:
    """Only the local spectator super-admin is omitted from rankings/stats (not real admins)."""
    s = get_settings()
    return email.lower().strip() == s.super_admin_email.lower().strip()
