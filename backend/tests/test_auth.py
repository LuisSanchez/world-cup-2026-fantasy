"""Unit tests for auth helpers with mocked DB."""

from unittest.mock import MagicMock, patch

from app.auth import create_access_token, get_or_create_user_by_email


class TestCreateAccessToken:
    @patch("app.auth.settings")
    def test_returns_jwt_string(self, mock_settings):
        mock_settings.secret_key = "test-secret-key-for-jwt"
        token = create_access_token(1, "u@test.com")
        assert isinstance(token, str)
        assert len(token) > 20


class TestGetOrCreateUser:
    @patch("app.auth.is_admin_email", return_value=True)
    def test_promotes_existing_admin(self, mock_adm):
        existing = MagicMock()
        existing.email = "leafaronrutas123@gmail.com"
        existing.name = ""
        existing.picture = ""
        existing.google_id = None
        existing.is_admin = False

        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = existing

        user = get_or_create_user_by_email(db, "leafaronrutas123@gmail.com", name="L")
        assert existing.is_admin is True
        db.commit.assert_called()
        assert user is existing

    @patch("app.auth.is_admin_email", return_value=False)
    def test_creates_non_admin(self, mock_adm):
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        get_or_create_user_by_email(db, "player@x.com", name="P")
        db.add.assert_called_once()
        added = db.add.call_args[0][0]
        assert added.email == "player@x.com"
        assert added.is_admin is False
