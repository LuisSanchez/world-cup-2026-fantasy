"""Unit tests for dashboard stats with mocked DB."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.stats import UserStats, _compute_flags, build_user_stats, dashboard_payload, leader_for


class TestComputeFlags:
    def test_exact(self):
        f = _compute_flags(2, 1, 2, 1)
        assert f["exact"] is True
        assert f["result"] is True
        assert f["team_goals"] is True

    def test_result_only_partial(self):
        f = _compute_flags(1, 0, 2, 0)
        assert f["exact"] is False
        assert f["result"] is True
        assert f["gd"] is False  # GD +1 vs +2
        assert f["team_goals"] is True  # away 0 correct

    def test_same_goal_diff_not_exact(self):
        f = _compute_flags(1, 0, 2, 1)
        assert f["gd"] is True
        assert f["exact"] is False


class TestBuildUserStats:
    @patch("app.stats.is_leaderboard_excluded_email", return_value=False)
    def test_aggregates_predictions(self, _excl):
        finished = SimpleNamespace(
            id=10, home_score=2, away_score=1, is_finished=True
        )
        user = SimpleNamespace(
            id=1, email="a@b.com", name="Alice", picture="", total_points=5, is_admin=False
        )
        pred = SimpleNamespace(
            match_id=10, home_score=2, away_score=1, points_total=5
        )

        db = MagicMock()
        # Match query .filter().all()
        db.query.return_value.filter.return_value.all.side_effect = [
            [finished],  # finished matches
            [user],  # users
            [pred],  # predictions for user
        ]

        # Re-implement simpler: patch query chain more carefully
        def query_side_effect(model):
            m = MagicMock()
            if model.__name__ == "Match":
                m.filter.return_value.all.return_value = [finished]
            elif model.__name__ == "User":
                m.all.return_value = [user]
            elif model.__name__ == "Prediction":
                m.filter.return_value.all.return_value = [pred]
            return m

        from app.models import Match, Prediction, User

        def q(model):
            mq = MagicMock()
            if model is Match:
                mq.filter.return_value.all.return_value = [finished]
            elif model is User:
                mq.all.return_value = [user]
            elif model is Prediction:
                mq.filter.return_value.all.return_value = [pred]
            return mq

        db.query.side_effect = q
        stats = build_user_stats(db)
        assert len(stats) == 1
        assert stats[0].exact_scores == 1
        assert stats[0].result_hits == 1

    def test_excludes_spectator_admin(self):
        with patch("app.stats.is_leaderboard_excluded_email", side_effect=lambda e: e == "admin@localhost.dev"):
            user = SimpleNamespace(
                id=1, email="admin@localhost.dev", name="Admin", picture="", total_points=0
            )
            db = MagicMock()

            from app.models import Match, User

            def q(model):
                mq = MagicMock()
                if model is Match:
                    mq.filter.return_value.all.return_value = [
                        SimpleNamespace(id=1, home_score=1, away_score=0)
                    ]
                elif model is User:
                    mq.all.return_value = [user]
                return mq

            db.query.side_effect = q
            assert build_user_stats(db) == []


class TestLeaderFor:
    def test_picks_max(self):
        a = UserStats(1, "a@x", "A", "", 10, 5, 2, 3, 4, 1, 2.0, 0.5, 1.5, 50, 20)
        b = UserStats(2, "b@x", "B", "", 12, 5, 5, 3, 4, 1, 2.0, 0.5, 1.5, 50, 40)
        assert leader_for([a, b], "exact_scores").user_id == 2


class TestDashboardPayload:
    @patch("app.stats.build_user_stats")
    def test_structure(self, mock_build):
        mock_build.return_value = [
            UserStats(1, "a@x", "A", "", 10, 5, 2, 3, 4, 1, 2.0, 0.5, 1.5, 50, 20)
        ]
        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 10
        payload = dashboard_payload(db)
        assert payload["finished_matches"] == 10
        assert payload["players_count"] == 1
        assert "highlights" in payload
        assert "rankings" in payload
        assert len(payload["players"]) == 1
