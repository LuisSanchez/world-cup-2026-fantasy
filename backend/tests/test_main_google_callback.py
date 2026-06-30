"""Google OAuth callback path."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_app():
    with patch("app.main.seed_if_empty", return_value={}), patch(
        "app.main.auto_finish_elapsed_matches", return_value=0
    ), patch("app.results_sync.start_background_sync"), patch(
        "app.results_sync.stop_background_sync", new_callable=AsyncMock
    ), patch("app.seed._ensure_admin"), patch("app.main.admin_email_set", return_value=set()):
        from app.database import get_db
        from app.main import app

        db = MagicMock()
        app.dependency_overrides[get_db] = lambda: db
        with TestClient(app, follow_redirects=False) as c:
            yield c, db, app
        app.dependency_overrides.clear()


def test_google_callback_not_configured(client_app):
    c, _, _ = client_app
    with patch("app.main.settings") as s:
        s.google_client_id = ""
        s.google_client_secret = ""
        r = c.get("/api/auth/google/callback?code=abc")
    assert r.status_code == 400


def test_google_callback_success(client_app):
    c, db, _ = client_app
    u = SimpleNamespace(
        id=1, email="g@x.com", name="G", picture="", is_admin=False, total_points=0
    )
    token_res = MagicMock()
    token_res.status_code = 200
    token_res.json.return_value = {"access_token": "ga"}
    info_res = MagicMock()
    info_res.status_code = 200
    info_res.json.return_value = {"email": "g@x.com", "name": "G", "picture": "", "id": "1"}

    class ACM:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def post(self, *a, **k):
            return token_res

        async def get(self, *a, **k):
            return info_res

    with patch("app.main.settings") as s, patch("app.main.httpx.AsyncClient", return_value=ACM()), patch(
        "app.main.get_or_create_user_by_email", return_value=u
    ), patch("app.main.create_access_token", return_value="jwt"):
        s.google_client_id = "c"
        s.google_client_secret = "s"
        s.backend_url = "http://localhost:8000"
        s.frontend_url = "http://localhost:3000"
        r = c.get("/api/auth/google/callback?code=abc")
    assert r.status_code in (302, 307)
    assert "token=jwt" in r.headers.get("location", "")
