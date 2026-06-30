"""Extended auth unit tests."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt

from app.auth import (
    ALGORITHM,
    create_access_token,
    get_current_user,
    get_optional_user,
    require_admin,
)


class TestGetCurrentUser:
    def test_no_creds(self):
        with pytest.raises(HTTPException) as e:
            get_current_user(None, MagicMock())
        assert e.value.status_code == 401

    def test_invalid_token(self):
        creds = MagicMock()
        creds.credentials = "not-a-jwt"
        with patch("app.auth.settings") as s:
            s.secret_key = "k"
            with pytest.raises(HTTPException):
                get_current_user(creds, MagicMock())

    def test_user_not_found(self):
        with patch("app.auth.settings") as s:
            s.secret_key = "secret"
            tok = create_access_token(99, "x@y.com")
        creds = MagicMock()
        creds.credentials = tok
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        with patch("app.auth.settings") as s:
            s.secret_key = "secret"
            with pytest.raises(HTTPException) as e:
                get_current_user(creds, db)
        assert e.value.status_code == 401

    def test_promotes_admin_email(self):
        with patch("app.auth.settings") as s:
            s.secret_key = "secret"
            tok = create_access_token(1, "a@b.com")
        creds = MagicMock()
        creds.credentials = tok
        user = MagicMock()
        user.email = "a@b.com"
        user.is_admin = False
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = user
        with patch("app.auth.settings") as s, patch("app.auth.is_admin_email", return_value=True):
            s.secret_key = "secret"
            out = get_current_user(creds, db)
        assert user.is_admin is True
        assert out is user

    def test_ok_non_admin(self):
        with patch("app.auth.settings") as s:
            s.secret_key = "secret"
            tok = create_access_token(1, "p@x.com")
        creds = MagicMock()
        creds.credentials = tok
        user = MagicMock()
        user.email = "p@x.com"
        user.is_admin = False
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = user
        with patch("app.auth.settings") as s, patch("app.auth.is_admin_email", return_value=False):
            s.secret_key = "secret"
            assert get_current_user(creds, db) is user


class TestGetOptionalUser:
    def test_no_creds(self):
        assert get_optional_user(None, MagicMock()) is None

    def test_bad_token(self):
        creds = MagicMock()
        creds.credentials = "bad"
        with patch("app.auth.settings") as s:
            s.secret_key = "k"
            assert get_optional_user(creds, MagicMock()) is None

    def test_ok(self):
        with patch("app.auth.settings") as s:
            s.secret_key = "secret"
            tok = create_access_token(1, "p@x.com")
        creds = MagicMock()
        creds.credentials = tok
        user = MagicMock()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = user
        with patch("app.auth.settings") as s:
            s.secret_key = "secret"
            assert get_optional_user(creds, db) is user


class TestRequireAdmin:
    def test_non_admin_raises(self):
        u = MagicMock()
        u.is_admin = False
        with pytest.raises(HTTPException) as e:
            require_admin(u)
        assert e.value.status_code == 403

    def test_admin_passes(self):
        u = MagicMock()
        u.is_admin = True
        assert require_admin(u) is u


class TestGetOrCreateExtra:
    @patch("app.auth.is_admin_email", return_value=False)
    def test_updates_picture_and_google(self, _):
        from app.auth import get_or_create_user_by_email

        existing = MagicMock()
        existing.name = "N"
        existing.picture = ""
        existing.google_id = None
        existing.is_admin = False
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing
        get_or_create_user_by_email(db, "p@x.com", picture="http://pic", google_id="g1")
        assert existing.picture == "http://pic"
        assert existing.google_id == "g1"
