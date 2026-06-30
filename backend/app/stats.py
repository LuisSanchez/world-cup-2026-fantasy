"""Aggregate prediction accuracy stats for the dashboard."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import is_leaderboard_excluded_email
from app.models import Match, Prediction, User
from app.scoring import outcome


@dataclass
class UserStats:
    user_id: int
    email: str
    name: str
    picture: str
    total_points: int
    evaluated: int  # finished matches with a prediction
    exact_scores: int  # perfect scoreline
    team_goals_hits: int  # at least one team's goals correct
    result_hits: int  # correct W/D/L
    goal_diff_hits: int  # correct goal difference
    avg_points_when_result_correct: float  # "avg winning" = avg pts on correct result
    avg_points_when_result_wrong: float  # "avg losing" = avg pts on wrong result
    avg_points_overall: float
    hit_rate_result: float  # % of evaluated with correct result
    hit_rate_exact: float


def _compute_flags(ph: int, pa: int, rh: int, ra: int) -> dict:
    exact = ph == rh and pa == ra
    team_goals = ph == rh or pa == ra
    result_ok = outcome(ph, pa) == outcome(rh, ra)
    gd_ok = (ph - pa) == (rh - ra)
    return {
        "exact": exact,
        "team_goals": team_goals,
        "result": result_ok,
        "gd": gd_ok,
    }


def build_user_stats(db: Session) -> list[UserStats]:
    finished = (
        db.query(Match)
        .filter(
            Match.is_finished == True,  # noqa: E712
            Match.home_score.isnot(None),
            Match.away_score.isnot(None),
        )
        .all()
    )
    finished_ids = {m.id: m for m in finished}
    if not finished_ids:
        return []

    users = db.query(User).all()
    out: list[UserStats] = []

    for user in users:
        if is_leaderboard_excluded_email(user.email):
            continue
        preds = (
            db.query(Prediction)
            .filter(
                Prediction.user_id == user.id,
                Prediction.match_id.in_(list(finished_ids.keys())),
            )
            .all()
        )
        if not preds:
            continue

        exact = team_goals = result_hits = gd_hits = 0
        pts_win: list[int] = []
        pts_lose: list[int] = []
        pts_all: list[int] = []

        for pred in preds:
            m = finished_ids.get(pred.match_id)
            if not m or m.home_score is None or m.away_score is None:
                continue
            flags = _compute_flags(
                pred.home_score, pred.away_score, m.home_score, m.away_score
            )
            if flags["exact"]:
                exact += 1
            if flags["team_goals"]:
                team_goals += 1
            if flags["result"]:
                result_hits += 1
            if flags["gd"]:
                gd_hits += 1

            pts = pred.points_total or 0
            pts_all.append(pts)
            if flags["result"]:
                pts_win.append(pts)
            else:
                pts_lose.append(pts)

        n = len(pts_all)
        if n == 0:
            continue

        out.append(
            UserStats(
                user_id=user.id,
                email=user.email,
                name=user.name or user.email.split("@")[0],
                picture=user.picture or "",
                total_points=user.total_points,
                evaluated=n,
                exact_scores=exact,
                team_goals_hits=team_goals,
                result_hits=result_hits,
                goal_diff_hits=gd_hits,
                avg_points_when_result_correct=(
                    round(sum(pts_win) / len(pts_win), 2) if pts_win else 0.0
                ),
                avg_points_when_result_wrong=(
                    round(sum(pts_lose) / len(pts_lose), 2) if pts_lose else 0.0
                ),
                avg_points_overall=round(sum(pts_all) / n, 2),
                hit_rate_result=round(100.0 * result_hits / n, 1),
                hit_rate_exact=round(100.0 * exact / n, 1),
            )
        )

    return out


def leader_for(users: list[UserStats], key: str, reverse: bool = True) -> UserStats | None:
    if not users:
        return None
    return sorted(users, key=lambda u: (getattr(u, key), u.total_points), reverse=reverse)[0]


def dashboard_payload(db: Session) -> dict:
    users = build_user_stats(db)
    finished_count = (
        db.query(Match)
        .filter(Match.is_finished == True, Match.home_score.isnot(None))  # noqa: E712
        .count()
    )

    def rank_list(key: str, limit: int = 10) -> list[dict]:
        ranked = sorted(
            users,
            key=lambda u: (getattr(u, key), u.total_points, u.evaluated),
            reverse=True,
        )
        return [
            {
                "rank": i + 1,
                "user_id": u.user_id,
                "name": u.name,
                "email": u.email,
                "picture": u.picture,
                "value": getattr(u, key),
                "evaluated": u.evaluated,
                "total_points": u.total_points,
            }
            for i, u in enumerate(ranked[:limit])
        ]

    leaders = {
        "exact_scores": leader_for(users, "exact_scores"),
        "team_goals_hits": leader_for(users, "team_goals_hits"),
        "result_hits": leader_for(users, "result_hits"),
        "goal_diff_hits": leader_for(users, "goal_diff_hits"),
        "avg_points_when_result_correct": leader_for(users, "avg_points_when_result_correct"),
        "avg_points_when_result_wrong": leader_for(users, "avg_points_when_result_wrong"),
        "avg_points_overall": leader_for(users, "avg_points_overall"),
        "total_points": leader_for(users, "total_points"),
    }

    def leader_dict(u: UserStats | None, key: str) -> dict | None:
        if not u:
            return None
        return {
            "user_id": u.user_id,
            "name": u.name,
            "email": u.email,
            "picture": u.picture,
            "value": getattr(u, key),
            "evaluated": u.evaluated,
            "total_points": u.total_points,
        }

    return {
        "finished_matches": finished_count,
        "players_count": len(users),
        "highlights": {
            "most_exact": leader_dict(leaders["exact_scores"], "exact_scores"),
            "most_team_goals": leader_dict(leaders["team_goals_hits"], "team_goals_hits"),
            "most_results": leader_dict(leaders["result_hits"], "result_hits"),
            "most_goal_diff": leader_dict(leaders["goal_diff_hits"], "goal_diff_hits"),
            "best_avg_when_winning": leader_dict(
                leaders["avg_points_when_result_correct"], "avg_points_when_result_correct"
            ),
            "best_avg_when_losing": leader_dict(
                leaders["avg_points_when_result_wrong"], "avg_points_when_result_wrong"
            ),
            "best_avg_overall": leader_dict(leaders["avg_points_overall"], "avg_points_overall"),
            "most_points": leader_dict(leaders["total_points"], "total_points"),
        },
        "rankings": {
            "exact_scores": rank_list("exact_scores"),
            "team_goals_hits": rank_list("team_goals_hits"),
            "result_hits": rank_list("result_hits"),
            "goal_diff_hits": rank_list("goal_diff_hits"),
            "avg_points_when_result_correct": rank_list("avg_points_when_result_correct"),
            "avg_points_when_result_wrong": rank_list("avg_points_when_result_wrong"),
            "avg_points_overall": rank_list("avg_points_overall"),
            "total_points": rank_list("total_points"),
        },
        "players": [
            {
                "user_id": u.user_id,
                "name": u.name,
                "email": u.email,
                "picture": u.picture,
                "total_points": u.total_points,
                "evaluated": u.evaluated,
                "exact_scores": u.exact_scores,
                "team_goals_hits": u.team_goals_hits,
                "result_hits": u.result_hits,
                "goal_diff_hits": u.goal_diff_hits,
                "avg_points_when_result_correct": u.avg_points_when_result_correct,
                "avg_points_when_result_wrong": u.avg_points_when_result_wrong,
                "avg_points_overall": u.avg_points_overall,
                "hit_rate_result": u.hit_rate_result,
                "hit_rate_exact": u.hit_rate_exact,
            }
            for u in sorted(users, key=lambda x: x.total_points, reverse=True)
        ],
    }
