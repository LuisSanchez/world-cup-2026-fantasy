"""API route tests via FastAPI TestClient (DB/sync/seed/auth heavily mocked)."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _user(admin=False, uid=1, email="p@x.com"):
    return SimpleNamespace(
        id=uid,
        email=email,
        name="Player",
        picture="",
        is_admin=admin,
        total_points=10,
        google_id=None,
    )


def _match_row(**kwargs):
    base = dict(
        id=1,
        match_number=1,
        home_team="México",
        away_team="Sudáfrica",
        home_flag="mx",
        away_flag="za",
        kickoff=datetime(2026, 6, 21, 18, 0, 0),
        stage="group",
        group_name="",
        home_score=None,
        away_score=None,
        is_finished=False,
        is_placeholder=False,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


@pytest.fixture
def client_and_db():
    """App with lifespan/seed/sync disabled and get_db overridden."""
    with patch("app.main.seed_if_empty", return_value={"seeded": False}), patch(
        "app.main.auto_finish_elapsed_matches", return_value=0
    ), patch("app.results_sync.start_background_sync"), patch(
        "app.results_sync.stop_background_sync", new_callable=AsyncMock
    ), patch("app.seed._ensure_admin"), patch(
        "app.main.admin_email_set", return_value=set()
    ):
        from app.database import get_db
        from app.main import app

        db = MagicMock()
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app) as c:
            yield c, db, app
        app.dependency_overrides.clear()


class TestHealthAndAuthRoutes:
    def test_health(self, client_and_db):
        c, _, _ = client_and_db
        r = c.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_google_auth_url_dev_mode(self, client_and_db):
        c, _, _ = client_and_db
        with patch("app.main.settings") as s:
            s.google_client_id = ""
            r = c.get("/api/auth/google/url")
        assert r.status_code == 200
        assert r.json()["dev_login"] is True

    def test_google_auth_url_with_client(self, client_and_db):
        c, _, _ = client_and_db
        with patch("app.main.settings") as s:
            s.google_client_id = "cid"
            s.backend_url = "http://localhost:8000"
            r = c.get("/api/auth/google/url")
        assert r.status_code == 200
        assert "accounts.google.com" in r.json()["url"]

    def test_dev_login(self, client_and_db):
        c, db, _ = client_and_db
        u = _user()
        with patch("app.main.get_or_create_user_by_email", return_value=u), patch(
            "app.main.create_access_token", return_value="tok123"
        ):
            r = c.post("/api/auth/dev-login", json={"email": "p@x.com"})
        assert r.status_code == 200
        assert r.json()["access_token"] == "tok123"

    def test_me_requires_auth(self, client_and_db):
        c, _, _ = client_and_db
        assert c.get("/api/auth/me").status_code == 401

    def test_me_ok(self, client_and_db):
        c, _, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user()
        r = c.get("/api/auth/me")
        assert r.status_code == 200
        assert r.json()["email"] == "p@x.com"


class TestMatchesAndPredictions:
    def test_list_matches(self, client_and_db):
        c, db, _ = client_and_db
        m = _match_row()
        db.query.return_value.order_by.return_value.all.return_value = [m]
        db.query.return_value.order_by.return_value.filter.return_value.all.return_value = [m]
        with patch("app.results_sync.maybe_sync_on_request", new_callable=AsyncMock), patch(
            "app.main.match_status", return_value="upcoming"
        ), patch("app.main.can_edit_prediction", return_value=True):
            r = c.get("/api/matches")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_match_404(self, client_and_db):
        c, db, _ = client_and_db
        db.query.return_value.filter.return_value.first.return_value = None
        assert c.get("/api/matches/999").status_code == 404

    def test_get_match_ok(self, client_and_db):
        c, db, _ = client_and_db
        db.query.return_value.filter.return_value.first.return_value = _match_row()
        with patch("app.main.match_status", return_value="upcoming"), patch(
            "app.main.can_edit_prediction", return_value=True
        ):
            r = c.get("/api/matches/1")
        assert r.status_code == 200
        assert r.json()["match_number"] == 1

    def test_my_predictions(self, client_and_db):
        c, db, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user()
        m = _match_row()
        db.query.return_value.order_by.return_value.all.return_value = [m]
        db.query.return_value.filter.return_value.all.return_value = []
        with patch("app.results_sync.maybe_sync_on_request", new_callable=AsyncMock), patch(
            "app.main.match_status", return_value="upcoming"
        ), patch("app.main.can_edit_prediction", return_value=True):
            r = c.get("/api/predictions/me")
        assert r.status_code == 200

    def test_upsert_prediction_forbidden_when_locked(self, client_and_db):
        c, db, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user()
        db.query.return_value.filter.return_value.first.return_value = _match_row()
        with patch("app.main.can_edit_prediction", return_value=False), patch(
            "app.main.match_status", return_value="locked"
        ):
            r = c.put("/api/predictions/1", json={"home_score": 1, "away_score": 0})
        assert r.status_code == 403

    def test_upsert_prediction_ok_new(self, client_and_db):
        c, db, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user()
        match = _match_row(is_finished=False, home_score=None)
        existing_pred = SimpleNamespace(
            id=10,
            user_id=1,
            match_id=1,
            home_score=0,
            away_score=0,
            points_goals=0,
            points_result=0,
            points_total=0,
            updated_at=None,
        )
        # first() for match, then for existing pred (update path avoids response issues)
        db.query.return_value.filter.return_value.first.side_effect = [match, existing_pred]
        with patch("app.main.can_edit_prediction", return_value=True):
            r = c.put("/api/predictions/1", json={"home_score": 2, "away_score": 1})
        assert r.status_code == 200
        assert existing_pred.home_score == 2

    def test_upsert_prediction_match_not_found(self, client_and_db):
        c, db, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user()
        db.query.return_value.filter.return_value.first.return_value = None
        r = c.put("/api/predictions/999", json={"home_score": 1, "away_score": 0})
        assert r.status_code == 404


class TestLeaderboardDashboardAdmin:
    def test_leaderboard_excludes_spectator(self, client_and_db):
        c, db, _ = client_and_db
        players = [
            _user(email="admin@localhost.dev"),
            _user(uid=2, email="real@x.com"),
        ]
        players[0].total_points = 0
        players[1].total_points = 5
        db.query.return_value.order_by.return_value.all.return_value = players
        db.query.return_value.filter.return_value.count.return_value = 3
        with patch("app.results_sync.maybe_sync_on_request", new_callable=AsyncMock), patch(
            "app.main.is_leaderboard_excluded_email",
            side_effect=lambda e: e == "admin@localhost.dev",
        ):
            r = c.get("/api/leaderboard")
        assert r.status_code == 200
        data = r.json()
        assert all(row["email"] != "admin@localhost.dev" for row in data)

    def test_dashboard(self, client_and_db):
        c, _, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user()
        # main imports dashboard_payload inside handler from app.stats
        with patch("app.results_sync.maybe_sync_on_request", new_callable=AsyncMock), patch(
            "app.stats.dashboard_payload", return_value={"finished_matches": 1, "players": []}
        ):
            r = c.get("/api/dashboard")
        assert r.status_code == 200

    def test_admin_users_forbidden(self, client_and_db):
        c, _, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user(admin=False)
        assert c.get("/api/admin/users").status_code == 403

    def test_admin_users_ok(self, client_and_db):
        c, db, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user(admin=True)
        db.query.return_value.order_by.return_value.all.return_value = [_user(admin=True)]
        r = c.get("/api/admin/users")
        assert r.status_code == 200

    def test_admin_set_score(self, client_and_db):
        c, db, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user(admin=True)
        match = _match_row()
        db.query.return_value.filter.return_value.first.return_value = match
        with patch("app.main.recalculate_match_predictions"), patch(
            "app.main.match_status", return_value="finished"
        ), patch("app.main.can_edit_prediction", return_value=False):
            r = c.post("/api/admin/matches/1/score", json={"home_score": 2, "away_score": 1, "is_finished": True})
        assert r.status_code == 200
        assert match.home_score == 2

    def test_admin_update_match(self, client_and_db):
        c, db, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user(admin=True)
        match = _match_row(is_placeholder=True)
        db.query.return_value.filter.return_value.first.return_value = match
        with patch("app.main.get_flag_code", return_value="br"), patch(
            "app.main.match_status", return_value="upcoming"
        ), patch("app.main.can_edit_prediction", return_value=True):
            r = c.patch("/api/admin/matches/1", json={"home_team": "Brasil", "away_team": "Haití"})
        assert r.status_code == 200

    def test_admin_recalculate(self, client_and_db):
        c, _, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user(admin=True)
        with patch("app.main.recalculate_all_scores"):
            r = c.post("/api/admin/recalculate")
        assert r.status_code == 200

    def test_admin_sync_results(self, client_and_db):
        c, _, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user(admin=True)
        with patch("app.results_sync.sync_finished_scores", return_value={"updated": 0}):
            r = c.post("/api/admin/sync-results")
        assert r.status_code == 200

    def test_admin_sync_status(self, client_and_db):
        c, _, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user(admin=True)
        r = c.get("/api/admin/sync-status")
        assert r.status_code == 200
        assert "football_api_configured" in r.json()

    def test_admin_user_predictions(self, client_and_db):
        c, db, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user(admin=True)
        target = _user(uid=9, email="t@x.com")
        m = _match_row()

        def first_side_effect(*a, **k):
            return target

        db.query.return_value.filter.return_value.first.return_value = target
        db.query.return_value.order_by.return_value.all.return_value = [m]
        db.query.return_value.filter.return_value.all.return_value = []
        with patch("app.main.match_status", return_value="finished"), patch(
            "app.main.can_edit_prediction", return_value=False
        ):
            r = c.get("/api/admin/users/9/predictions")
        assert r.status_code == 200

    def test_admin_seed(self, client_and_db):
        c, _, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user(admin=True)
        with patch("app.main.seed_if_empty", return_value={"seeded": False}):
            r = c.post("/api/admin/seed")
        assert r.status_code == 200

    def test_admin_export_excel_forbidden_non_admin(self, client_and_db):
        c, _, app = client_and_db
        from app.auth import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _user(admin=False)
        assert c.get("/api/admin/export/scores.xlsx").status_code == 403

    def test_admin_export_excel_ok(self, client_and_db):
        c, _, app = client_and_db
        from app.auth import get_current_user
        from io import BytesIO

        app.dependency_overrides[get_current_user] = lambda: _user(admin=True)
        fake = BytesIO(b"PK fake xlsx")
        with patch("app.export_excel.build_scores_workbook", return_value=fake), patch(
            "app.export_excel.export_filename", return_value="test.xlsx"
        ):
            r = c.get("/api/admin/export/scores.xlsx")
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")
