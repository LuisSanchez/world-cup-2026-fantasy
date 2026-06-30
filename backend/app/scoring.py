"""Scoring rules (cumulative, max 5 pts per match):

+1  Correct winner or draw
+1  Correct goals for at least one team
+1  Correct goal difference
+2  Exact scoreline (bonus; with exact score you typically get all tiers = 5)

Without exact score, max is 3 pts (winner/draw + one team goals + goal diff).
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Match, Prediction, User


def outcome(home: int, away: int) -> str:
    if home > away:
        return "H"
    if home < away:
        return "A"
    return "D"


def score_prediction(pred_home: int, pred_away: int, real_home: int, real_away: int) -> tuple[int, int, int]:
    """Returns (points_goals breakdown bucket, points_result bucket, total).

    Stored columns:
    - points_result: winner/draw tier (0 or 1)
    - points_goals: goals-at-least-one + goal-diff + exact bonus (0–4)
    - points_total: sum (0–5)
    """
    points_result = 0
    points_goals = 0

    # +1 correct winner or draw
    if outcome(pred_home, pred_away) == outcome(real_home, real_away):
        points_result = 1

    # +1 correct goals scored by at least one team
    if pred_home == real_home or pred_away == real_away:
        points_goals += 1

    # +1 correct goal difference
    if (pred_home - pred_away) == (real_home - real_away):
        points_goals += 1

    # +2 exact scoreline
    if pred_home == real_home and pred_away == real_away:
        points_goals += 2

    total = points_result + points_goals
    return points_goals, points_result, total


def match_status(match: Match, now: datetime | None = None) -> str:
    """Return: upcoming | locked | live | finished"""
    settings = get_settings()
    now = now or datetime.utcnow()

    if match.is_finished or (match.home_score is not None and match.away_score is not None):
        return "finished"

    if not match.kickoff:
        return "upcoming"

    lock_time = match.kickoff - timedelta(minutes=settings.prediction_lock_minutes)
    end_time = match.kickoff + timedelta(minutes=settings.match_duration_minutes)

    if now >= end_time:
        return "finished"
    if now >= match.kickoff:
        return "live"
    if now >= lock_time:
        return "locked"
    return "upcoming"


def can_edit_prediction(match: Match, now: datetime | None = None) -> bool:
    return match_status(match, now) == "upcoming"


def recalculate_match_predictions(db: Session, match: Match) -> None:
    if match.home_score is None or match.away_score is None:
        return

    preds = db.query(Prediction).filter(Prediction.match_id == match.id).all()
    for pred in preds:
        g, r, t = score_prediction(
            pred.home_score, pred.away_score, match.home_score, match.away_score
        )
        pred.points_goals = g
        pred.points_result = r
        pred.points_total = t
    db.flush()
    _recalculate_user_totals(db)


def recalculate_all_scores(db: Session) -> None:
    matches = db.query(Match).filter(Match.is_finished == True).all()  # noqa: E712
    for match in matches:
        if match.home_score is None or match.away_score is None:
            continue
        preds = db.query(Prediction).filter(Prediction.match_id == match.id).all()
        for pred in preds:
            g, r, t = score_prediction(
                pred.home_score, pred.away_score, match.home_score, match.away_score
            )
            pred.points_goals = g
            pred.points_result = r
            pred.points_total = t
    db.flush()
    _recalculate_user_totals(db)


def _recalculate_user_totals(db: Session) -> None:
    users = db.query(User).all()
    for user in users:
        total = (
            db.query(Prediction)
            .filter(Prediction.user_id == user.id)
            .with_entities(Prediction.points_total)
            .all()
        )
        user.total_points = sum(p[0] or 0 for p in total)
    db.flush()


def auto_finish_elapsed_matches(db: Session) -> int:
    """Mark matches past duration as finished if scores are set; used by scheduler/poll."""
    settings = get_settings()
    now = datetime.utcnow()
    updated = 0
    matches = db.query(Match).filter(Match.is_finished == False).all()  # noqa: E712
    for m in matches:
        if not m.kickoff:
            continue
        end_time = m.kickoff + timedelta(minutes=settings.match_duration_minutes)
        if now >= end_time and m.home_score is not None and m.away_score is not None:
            m.is_finished = True
            recalculate_match_predictions(db, m)
            updated += 1
        elif now >= end_time and m.home_score is None:
            # Time elapsed but no score entered yet — still mark as past for edit lock
            pass
    if updated:
        db.commit()
    return updated
