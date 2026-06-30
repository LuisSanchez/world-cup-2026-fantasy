"""More scoring / totals / auto_finish coverage."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.scoring import (
    auto_finish_elapsed_matches,
    recalculate_all_scores,
    recalculate_match_predictions,
)


class TestRecalculateAll:
    @patch("app.scoring._recalculate_user_totals")
    def test_all_finished_matches(self, mock_tot):
        m1 = SimpleNamespace(id=1, home_score=1, away_score=0, is_finished=True)
        m2 = SimpleNamespace(id=2, home_score=None, away_score=None, is_finished=True)
        pred = SimpleNamespace(home_score=1, away_score=0, points_goals=0, points_result=0, points_total=0)
        db = MagicMock()
        db.query.return_value.filter.return_value.all.side_effect = [
            [m1, m2],  # matches
            [pred],  # preds for m1
        ]
        # second call for m2 preds skipped because scores None — only one filter().all for preds inside loop
        # Actually loop: for each match, if scores ok, query preds
        def filter_all_chain():
            pass

        q = MagicMock()
        db.query.return_value = q
        q.filter.return_value.all.side_effect = [
            [m1, m2],
            [pred],
        ]
        recalculate_all_scores(db)
        assert pred.points_total == 5
        mock_tot.assert_called_once()


class TestUserTotals:
    def test_recalculate_user_totals(self):
        from app.scoring import _recalculate_user_totals

        u = SimpleNamespace(id=1, total_points=0)
        db = MagicMock()
        db.query.return_value.all.return_value = [u]
        db.query.return_value.filter.return_value.with_entities.return_value.all.return_value = [
            (3,),
            (2,),
        ]
        # Need two different query behaviors - simplify by side_effect on query
        calls = {"n": 0}

        def query_side(model=None):
            m = MagicMock()
            calls["n"] += 1
            if calls["n"] == 1:
                m.all.return_value = [u]
            else:
                m.filter.return_value.with_entities.return_value.all.return_value = [(3,), (2,)]
            return m

        db.query.side_effect = query_side
        _recalculate_user_totals(db)
        assert u.total_points == 5


class TestAutoFinish:
    @patch("app.scoring.recalculate_match_predictions")
    @patch("app.scoring.get_settings")
    def test_marks_elapsed_with_scores(self, gs, mock_recalc):
        gs.return_value = SimpleNamespace(match_duration_minutes=110)
        kick = datetime.utcnow() - timedelta(hours=3)
        m = SimpleNamespace(
            kickoff=kick,
            is_finished=False,
            home_score=2,
            away_score=1,
        )
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [m]
        n = auto_finish_elapsed_matches(db)
        assert n == 1
        assert m.is_finished is True
        db.commit.assert_called()

    @patch("app.scoring.get_settings")
    def test_no_kickoff_skipped(self, gs):
        gs.return_value = SimpleNamespace(match_duration_minutes=110)
        m = SimpleNamespace(kickoff=None, is_finished=False, home_score=None, away_score=None)
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [m]
        assert auto_finish_elapsed_matches(db) == 0

    @patch("app.scoring.get_settings")
    def test_elapsed_no_score_no_finish(self, gs):
        gs.return_value = SimpleNamespace(match_duration_minutes=110)
        kick = datetime.utcnow() - timedelta(hours=3)
        m = SimpleNamespace(kickoff=kick, is_finished=False, home_score=None, away_score=None)
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [m]
        assert auto_finish_elapsed_matches(db) == 0
