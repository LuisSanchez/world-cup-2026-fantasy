"""Teams helpers + pydantic schemas smoke tests."""

from datetime import datetime

from app.schemas import (
    AdminSetScore,
    AdminUpdateMatch,
    DevLoginRequest,
    LeaderboardEntry,
    MatchOut,
    PredictionOut,
    PredictionUpdate,
    TokenResponse,
    UserOut,
)
from app.teams import flag_emoji_from_code, get_flag_code, stage_from_match_number


class TestTeams:
    def test_get_flag_code(self):
        assert get_flag_code("México") == "mx"
        assert get_flag_code("Nope") == ""

    def test_flag_emoji(self):
        assert flag_emoji_from_code("") == ""
        assert flag_emoji_from_code("gb-eng") == ""
        assert flag_emoji_from_code("x") == ""
        e = flag_emoji_from_code("mx")
        assert len(e) >= 2

    def test_stage_from_match_number(self):
        assert stage_from_match_number(1, "x") == "group"
        assert stage_from_match_number(80, "16vos") == "r16"
        assert stage_from_match_number(90, "8vos") == "qf"
        assert stage_from_match_number(98, "4tos") == "sf"
        assert stage_from_match_number(101, "Semi") == "sf"
        assert stage_from_match_number(104, "3ero") == "third"
        assert stage_from_match_number(103, "Final") == "final"
        assert stage_from_match_number(200, "other") == "knockout"


class TestSchemas:
    def test_user_out(self):
        u = UserOut(id=1, email="a@b.com", name="A", picture="", is_admin=False, total_points=0)
        assert u.email == "a@b.com"

    def test_match_out(self):
        m = MatchOut(
            id=1,
            match_number=1,
            home_team="A",
            away_team="B",
            home_flag="a",
            away_flag="b",
            kickoff=datetime.utcnow(),
            lock_at=None,
            stage="group",
            group_name="",
            home_score=None,
            away_score=None,
            is_finished=False,
            is_placeholder=False,
            status="upcoming",
            can_edit=True,
        )
        assert m.can_edit is True

    def test_prediction_update_bounds(self):
        p = PredictionUpdate(home_score=0, away_score=3)
        assert p.away_score == 3

    def test_admin_set_score(self):
        a = AdminSetScore(home_score=1, away_score=1)
        assert a.is_finished is True

    def test_admin_update_partial(self):
        a = AdminUpdateMatch(home_team="X")
        assert a.away_team is None

    def test_dev_login(self):
        d = DevLoginRequest(email="t@t.com")
        assert d.email == "t@t.com"

    def test_leaderboard_entry(self):
        e = LeaderboardEntry(
            rank=1, user_id=1, email="a@b", name="A", picture="", total_points=5, predictions_count=2
        )
        assert e.rank == 1

    def test_token_response(self):
        t = TokenResponse(
            access_token="x",
            user=UserOut(id=1, email="a@b", name="", picture="", is_admin=False, total_points=0),
        )
        assert t.token_type == "bearer"

    def test_prediction_out(self):
        p = PredictionOut(
            id=1, match_id=2, home_score=1, away_score=0, points_goals=0, points_result=1, points_total=1
        )
        assert p.points_total == 1
