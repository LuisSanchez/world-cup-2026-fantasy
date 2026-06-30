"""Unit tests for scoring rules and match status (pure functions)."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.scoring import (
    can_edit_prediction,
    match_status,
    outcome,
    score_prediction,
)


class TestOutcome:
    def test_home_win(self):
        assert outcome(2, 1) == "H"

    def test_away_win(self):
        assert outcome(0, 1) == "A"

    def test_draw(self):
        assert outcome(1, 1) == "D"


class TestScorePrediction:
    """Examples from product rules: actual 2-1 and 1-1."""

    @pytest.mark.parametrize(
        "pred,expected_total",
        [
            ((2, 1), 5),
            ((1, 0), 2),
            ((2, 0), 2),
            ((0, 1), 1),
            ((2, 2), 1),
            ((0, 2), 0),
        ],
    )
    def test_actual_2_1(self, pred, expected_total):
        _, _, total = score_prediction(pred[0], pred[1], 2, 1)
        assert total == expected_total

    @pytest.mark.parametrize(
        "pred,expected_total",
        [
            ((1, 1), 5),
            ((0, 0), 2),
            ((2, 2), 2),
            ((1, 0), 1),
            ((2, 1), 1),
            ((0, 2), 0),
        ],
    )
    def test_actual_1_1(self, pred, expected_total):
        _, _, total = score_prediction(pred[0], pred[1], 1, 1)
        assert total == expected_total

    def test_result_bucket_on_correct_winner(self):
        goals, result, total = score_prediction(3, 0, 2, 0)
        assert result == 1  # same outcome H
        assert total >= 1

    def test_exact_gives_max_five(self):
        goals, result, total = score_prediction(1, 1, 1, 1)
        assert total == 5
        assert result == 1
        assert goals == 4


class TestMatchStatus:
    def _match(self, kickoff, finished=False, home=None, away=None):
        return SimpleNamespace(
            kickoff=kickoff,
            is_finished=finished,
            home_score=home,
            away_score=away,
        )

    @patch("app.scoring.get_settings")
    def test_upcoming_before_lock(self, mock_settings):
        mock_settings.return_value = SimpleNamespace(
            prediction_lock_minutes=10, match_duration_minutes=110
        )
        kick = datetime(2026, 6, 21, 18, 0, 0)
        now = kick - timedelta(minutes=30)
        with patch("app.scoring.datetime") as mock_dt:
            mock_dt.utcnow.return_value = now
            st = match_status(self._match(kick), now=now)
        assert st == "upcoming"

    @patch("app.scoring.get_settings")
    def test_locked_within_ten_minutes(self, mock_settings):
        mock_settings.return_value = SimpleNamespace(
            prediction_lock_minutes=10, match_duration_minutes=110
        )
        kick = datetime(2026, 6, 21, 18, 0, 0)
        now = kick - timedelta(minutes=5)
        assert match_status(self._match(kick), now=now) == "locked"

    @patch("app.scoring.get_settings")
    def test_live_after_kickoff(self, mock_settings):
        mock_settings.return_value = SimpleNamespace(
            prediction_lock_minutes=10, match_duration_minutes=110
        )
        kick = datetime(2026, 6, 21, 18, 0, 0)
        now = kick + timedelta(minutes=20)
        assert match_status(self._match(kick), now=now) == "live"

    @patch("app.scoring.get_settings")
    def test_finished_with_scores(self, mock_settings):
        mock_settings.return_value = SimpleNamespace(
            prediction_lock_minutes=10, match_duration_minutes=110
        )
        m = self._match(datetime(2026, 6, 21, 18, 0, 0), finished=True, home=1, away=0)
        assert match_status(m) == "finished"

    @patch("app.scoring.get_settings")
    def test_no_kickoff_upcoming(self, mock_settings):
        mock_settings.return_value = SimpleNamespace(
            prediction_lock_minutes=10, match_duration_minutes=110
        )
        m = self._match(None)
        assert match_status(m) == "upcoming"

    @patch("app.scoring.get_settings")
    def test_can_edit_only_upcoming(self, mock_settings):
        mock_settings.return_value = SimpleNamespace(
            prediction_lock_minutes=10, match_duration_minutes=110
        )
        kick = datetime(2026, 6, 21, 18, 0, 0)
        assert can_edit_prediction(self._match(kick), now=kick - timedelta(hours=2)) is True
        assert can_edit_prediction(self._match(kick), now=kick - timedelta(minutes=2)) is False


class TestRecalculateWithMocks:
    @patch("app.scoring._recalculate_user_totals")
    def test_recalculate_match_predictions_updates_preds(self, mock_totals):
        from app.scoring import recalculate_match_predictions

        match = SimpleNamespace(id=1, home_score=2, away_score=1)
        pred = SimpleNamespace(home_score=2, away_score=1, points_goals=0, points_result=0, points_total=0)
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [pred]

        recalculate_match_predictions(db, match)

        assert pred.points_total == 5
        mock_totals.assert_called_once_with(db)

    def test_recalculate_skips_without_scores(self):
        from app.scoring import recalculate_match_predictions

        match = SimpleNamespace(id=1, home_score=None, away_score=None)
        db = MagicMock()
        recalculate_match_predictions(db, match)
        db.query.assert_not_called()
