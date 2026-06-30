from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    get_or_create_user_by_email,
    require_admin,
)
from app.config import admin_email_set, get_settings, is_leaderboard_excluded_email
from app.database import Base, SessionLocal, engine, get_db
from app.models import Match, Prediction, User
from app.schemas import (
    AdminSetScore,
    AdminUpdateMatch,
    DevLoginRequest,
    LeaderboardEntry,
    MatchOut,
    PredictionOut,
    PredictionUpdate,
    PredictionWithMatch,
    TokenResponse,
    UserOut,
)
from app.scoring import (
    auto_finish_elapsed_matches,
    can_edit_prediction,
    match_status,
    recalculate_all_scores,
    recalculate_match_predictions,
)
from app.seed import import_quiniela_predictions, save_uploaded_quiniela, seed_if_empty
from app.teams import get_flag_code

settings = get_settings()


def match_to_out(m: Match) -> MatchOut:
    st = match_status(m)
    lock_at = None
    if m.kickoff:
        lock_at = m.kickoff - timedelta(minutes=settings.prediction_lock_minutes)
    return MatchOut(
        id=m.id,
        match_number=m.match_number,
        home_team=m.home_team,
        away_team=m.away_team,
        home_flag=m.home_flag,
        away_flag=m.away_flag,
        kickoff=m.kickoff,
        lock_at=lock_at,
        stage=m.stage,
        group_name=m.group_name,
        home_score=m.home_score,
        away_score=m.away_score,
        is_finished=m.is_finished or st == "finished",
        is_placeholder=m.is_placeholder,
        status=st,
        can_edit=can_edit_prediction(m),
    )


def run_startup_init() -> None:
    """DB bootstrap (tables, seed, kickoffs). Safe to call on each serverless cold start."""
    import logging
    import os

    logging.basicConfig(level=logging.INFO)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = seed_if_empty(db)
        print(f"Startup seed: {result}")
        from app.seed import _ensure_admin, refresh_kickoffs_from_schedule

        _ensure_admin(db)
        ko = refresh_kickoffs_from_schedule(db)
        print(f"Kickoff schedule refresh: {ko}")
        db.commit()
        print(f"Admin emails: {sorted(admin_email_set())}")
        auto_finish_elapsed_matches(db)
    finally:
        db.close()
    # Note: background results_sync is skipped when VERCEL=1 (serverless can't run a loop).
    # Use admin "Forzar sync" or rely on on-request maybe_sync_on_request instead.


@asynccontextmanager
async def lifespan(app: FastAPI):
    import os

    run_startup_init()

    from app.results_sync import start_background_sync, stop_background_sync

    # Vercel Python / Mangum: no long-lived background tasks
    if os.environ.get("VERCEL") != "1":
        start_background_sync()
        yield
        await stop_background_sync()
    else:
        yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

_cors_origins = [
    settings.frontend_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
# Common Vercel frontend URL if not set as FRONTEND_URL
if settings.frontend_url and "vercel.app" not in settings.frontend_url:
    pass  # user may set FRONTEND_URL explicitly

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──────────────────────────────────────────────

@app.get("/api/health")
def health():
    # Expose only dialect/host hint — never full URL/password
    from app.teams import SCHEDULE_REVISION

    url = settings.database_url or ""
    dialect = url.split(":", 1)[0] if url else "unknown"
    return {
        "status": "ok",
        "time": datetime.utcnow().isoformat(),
        "database": dialect,
        "schedule_revision": SCHEDULE_REVISION,
    }


# ── Auth ────────────────────────────────────────────────

@app.get("/api/auth/google/url")
def google_auth_url():
    if not settings.google_client_id:
        return {
            "url": None,
            "dev_login": True,
            "message": "Google OAuth not configured; use POST /api/auth/dev-login",
        }
    redirect_uri = f"{settings.backend_url}/api/auth/google/callback"
    params = (
        f"client_id={settings.google_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&access_type=offline"
        f"&prompt=select_account"
    )
    return {
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?{params}",
        "dev_login": False,
    }


@app.get("/api/auth/google/callback")
async def google_callback(code: str, db: Annotated[Session, Depends(get_db)]):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(400, "Google OAuth not configured")

    redirect_uri = f"{settings.backend_url}/api/auth/google/callback"
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code != 200:
            raise HTTPException(400, f"Token exchange failed: {token_res.text}")
        tokens = token_res.json()
        access = tokens.get("access_token")
        userinfo_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access}"},
        )
        if userinfo_res.status_code != 200:
            raise HTTPException(400, "Failed to fetch user info")
        info = userinfo_res.json()

    email = info.get("email", "").lower()
    if not email:
        raise HTTPException(400, "No email from Google")

    user = get_or_create_user_by_email(
        db,
        email=email,
        name=info.get("name", ""),
        picture=info.get("picture", ""),
        google_id=info.get("id"),
    )
    jwt_token = create_access_token(user.id, user.email)
    from fastapi.responses import RedirectResponse

    return RedirectResponse(
        url=f"{settings.frontend_url}/auth/callback?token={jwt_token}"
    )


@app.post("/api/auth/dev-login", response_model=TokenResponse)
def dev_login(body: DevLoginRequest, db: Annotated[Session, Depends(get_db)]):
    """Local/dev login by email (no Google). Also works for super admin."""
    user = get_or_create_user_by_email(db, email=body.email)
    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@app.get("/api/auth/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]):
    return user


# ── Matches ─────────────────────────────────────────────

@app.get("/api/matches", response_model=list[MatchOut])
async def list_matches(
    db: Annotated[Session, Depends(get_db)],
    stage: str | None = None,
):
    auto_finish_elapsed_matches(db)
    from app.results_sync import maybe_sync_on_request

    await maybe_sync_on_request(db)
    db.expire_all()
    q = db.query(Match).order_by(Match.match_number)
    if stage:
        q = q.filter(Match.stage == stage)
    return [match_to_out(m) for m in q.all()]


@app.get("/api/matches/{match_id}", response_model=MatchOut)
def get_match(match_id: int, db: Annotated[Session, Depends(get_db)]):
    m = db.query(Match).filter(Match.id == match_id).first()
    if not m:
        raise HTTPException(404, "Match not found")
    return match_to_out(m)


# ── Predictions (own user only) ─────────────────────────

@app.get("/api/predictions/me", response_model=list[PredictionWithMatch])
async def my_predictions(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    auto_finish_elapsed_matches(db)
    from app.results_sync import maybe_sync_on_request

    await maybe_sync_on_request(db)
    db.expire_all()
    matches = db.query(Match).order_by(Match.match_number).all()
    preds = {
        p.match_id: p
        for p in db.query(Prediction).filter(Prediction.user_id == user.id).all()
    }
    result = []
    for m in matches:
        pred = preds.get(m.id)
        result.append(
            PredictionWithMatch(
                prediction=PredictionOut.model_validate(pred) if pred else None,
                match=match_to_out(m),
            )
        )
    return result


@app.put("/api/predictions/{match_id}", response_model=PredictionOut)
def upsert_prediction(
    match_id: int,
    body: PredictionUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(404, "Match not found")
    if not can_edit_prediction(match):
        st = match_status(match)
        raise HTTPException(
            403,
            f"Cannot edit prediction: match is {st}. "
            f"Predictions lock {settings.prediction_lock_minutes} min before kickoff.",
        )

    pred = (
        db.query(Prediction)
        .filter(Prediction.user_id == user.id, Prediction.match_id == match_id)
        .first()
    )
    if pred:
        pred.home_score = body.home_score
        pred.away_score = body.away_score
        pred.updated_at = datetime.utcnow()
    else:
        pred = Prediction(
            user_id=user.id,
            match_id=match_id,
            home_score=body.home_score,
            away_score=body.away_score,
        )
        db.add(pred)

    # If match already finished (admin set score), recalculate this prediction
    if match.is_finished and match.home_score is not None:
        recalculate_match_predictions(db, match)

    db.commit()
    db.refresh(pred)
    return pred


# ── Leaderboard ─────────────────────────────────────────

@app.get("/api/dashboard")
async def dashboard(
    _: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Accuracy stats: exact scores, team goals, results, averages."""
    auto_finish_elapsed_matches(db)
    from app.results_sync import maybe_sync_on_request
    from app.stats import dashboard_payload

    await maybe_sync_on_request(db)
    db.expire_all()
    return dashboard_payload(db)


@app.get("/api/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(db: Annotated[Session, Depends(get_db)]):
    auto_finish_elapsed_matches(db)
    from app.results_sync import maybe_sync_on_request

    await maybe_sync_on_request(db)
    db.expire_all()
    # Real admins compete; only spectator super-admin (admin@localhost.dev) is excluded
    users = db.query(User).order_by(User.total_points.desc(), User.name).all()
    entries = []
    rank = 1
    for u in users:
        if is_leaderboard_excluded_email(u.email):
            continue
        count = db.query(Prediction).filter(Prediction.user_id == u.id).count()
        entries.append(
            LeaderboardEntry(
                rank=rank,
                user_id=u.id,
                email=u.email,
                name=u.name or u.email.split("@")[0],
                picture=u.picture,
                total_points=u.total_points,
                predictions_count=count,
            )
        )
        rank += 1
    return entries


# ── Admin ───────────────────────────────────────────────

@app.get("/api/admin/users", response_model=list[UserOut])
def admin_list_users(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    return db.query(User).order_by(User.email).all()


@app.get("/api/admin/users/{user_id}/predictions", response_model=list[PredictionWithMatch])
def admin_user_predictions(
    user_id: int,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "User not found")
    matches = db.query(Match).order_by(Match.match_number).all()
    preds = {
        p.match_id: p
        for p in db.query(Prediction).filter(Prediction.user_id == user_id).all()
    }
    return [
        PredictionWithMatch(
            prediction=PredictionOut.model_validate(preds[m.id]) if m.id in preds else None,
            match=match_to_out(m),
        )
        for m in matches
    ]


@app.patch("/api/admin/matches/{match_id}", response_model=MatchOut)
def admin_update_match(
    match_id: int,
    body: AdminUpdateMatch,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(404, "Match not found")

    if body.home_team is not None:
        match.home_team = body.home_team
        match.home_flag = get_flag_code(body.home_team)
        match.is_placeholder = "Por Definir" in body.home_team
    if body.away_team is not None:
        match.away_team = body.away_team
        match.away_flag = get_flag_code(body.away_team)
    if body.kickoff is not None:
        match.kickoff = body.kickoff
    if body.home_score is not None:
        match.home_score = body.home_score
    if body.away_score is not None:
        match.away_score = body.away_score
    if body.is_finished is not None:
        match.is_finished = body.is_finished

    if match.home_score is not None and match.away_score is not None and match.is_finished:
        recalculate_match_predictions(db, match)

    db.commit()
    db.refresh(match)
    return match_to_out(match)


@app.post("/api/admin/matches/{match_id}/score", response_model=MatchOut)
def admin_set_score(
    match_id: int,
    body: AdminSetScore,
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """Set real match score and recalculate all predictions + leaderboard."""
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(404, "Match not found")
    match.home_score = body.home_score
    match.away_score = body.away_score
    match.is_finished = body.is_finished
    recalculate_match_predictions(db, match)
    db.commit()
    db.refresh(match)
    return match_to_out(match)


@app.post("/api/admin/recalculate")
def admin_recalculate(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    recalculate_all_scores(db)
    db.commit()
    return {"ok": True}


@app.post("/api/admin/sync-results")
async def admin_sync_results(
    _: Annotated[User, Depends(require_admin)],
    force_all: bool = Query(True, description="Try all unfinished matches, not only past expected end"),
):
    """Force-fetch finished scores from external API and update leaderboard."""
    from app.results_sync import sync_finished_scores

    return await sync_finished_scores(force_all=force_all)


@app.get("/api/admin/sync-status")
def admin_sync_status(_: Annotated[User, Depends(require_admin)]):
    """Whether auto-sync is configured."""
    from app.web_results import web_results_status

    return {
        "football_api_configured": bool(settings.football_api_key),
        "league_id": settings.football_league_id,
        "season": settings.football_season,
        "match_duration_minutes": settings.match_duration_minutes,
        "results_fetch_window_minutes": settings.results_fetch_window_minutes,
        "results_poll_seconds": settings.results_poll_seconds,
        "web_scrape": web_results_status(),
    }


@app.post("/api/admin/seed")
def admin_reseed(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    force: bool = Query(False),
):
    if force:
        db.query(Prediction).delete()
        db.query(Match).delete()
        db.query(User).filter(User.is_admin == False).delete()  # noqa: E712
        db.commit()
    return seed_if_empty(db)


@app.post("/api/admin/import-quiniela")
async def admin_import_quiniela(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    update_existing: bool = Query(
        True,
        description="Overwrite existing predictions from the CSV (sheet is source of truth)",
    ),
    file: UploadFile = File(
        ...,
        description="Quiniela CSV/TSV (required). Stored as a new quiniela_<uuid>.csv; not reused.",
    ),
    also_sync_results: bool = Query(
        False,
        description="After import, run results sync + recalculate (may take a while)",
    ),
):
    """Save a new UUID-named quiniela upload (admin), then import predictions."""
    if not file.filename:
        raise HTTPException(400, "Se requiere un archivo CSV/TSV")

    try:
        raw = await file.read()
        saved_path = save_uploaded_quiniela(raw, filename=file.filename)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except OSError as e:
        raise HTTPException(500, f"No se pudo guardar el archivo: {e}") from e

    result = import_quiniela_predictions(
        db,
        update_existing=update_existing,
        csv_path=saved_path,
    )
    if not result.get("ok"):
        raise HTTPException(400, result.get("error") or "Import failed")

    out: dict = {**result, "saved_to": str(saved_path)}

    if also_sync_results:
        from app.results_sync import sync_finished_scores

        sync = await sync_finished_scores(force_all=True)
        recalculate_all_scores(db)
        db.commit()
        out["results_sync"] = sync
        out["recalculated"] = True

    return out


@app.post("/api/admin/refresh-kickoffs")
def admin_refresh_kickoffs(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """Re-apply canonical MATCH_KICKOFFS_UTC (after deploy / schedule fixes)."""
    from app.seed import refresh_kickoffs_from_schedule

    r = refresh_kickoffs_from_schedule(db)
    db.commit()
    return r


@app.get("/api/admin/export/scores.xlsx")
def admin_export_scores_excel(
    _: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
):
    """Excel: sheet Leaderboard + sheet Puntuaciones (per player / per match)."""
    from app.export_excel import build_scores_workbook, export_filename

    auto_finish_elapsed_matches(db)
    buf = build_scores_workbook(db)
    filename = export_filename()
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
