"""Unit tests for config / admin email helpers."""

from unittest.mock import patch

from app.config import admin_email_set, is_admin_email, is_leaderboard_excluded_email


class TestAdminEmails:
    @patch("app.config.get_settings")
    def test_admin_email_set_includes_defaults(self, mock_get):
        from types import SimpleNamespace

        mock_get.return_value = SimpleNamespace(
            super_admin_email="admin@localhost.dev",
            admin_emails="leafaronrutas123@gmail.com,luis.sanchezm86@gmail.com",
        )
        s = admin_email_set()
        assert "admin@localhost.dev" in s
        assert "leafaronrutas123@gmail.com" in s
        assert "luis.sanchezm86@gmail.com" in s

    @patch("app.config.get_settings")
    def test_is_admin_email_case_insensitive(self, mock_get):
        from types import SimpleNamespace

        mock_get.return_value = SimpleNamespace(
            super_admin_email="admin@localhost.dev",
            admin_emails="a@b.com",
        )
        assert is_admin_email("A@B.COM") is True
        assert is_admin_email("other@x.com") is False

    @patch("app.config.get_settings")
    def test_only_super_admin_excluded_from_leaderboard(self, mock_get):
        from types import SimpleNamespace

        mock_get.return_value = SimpleNamespace(
            super_admin_email="admin@localhost.dev",
            admin_emails="leafaronrutas123@gmail.com",
        )
        assert is_leaderboard_excluded_email("admin@localhost.dev") is True
        assert is_leaderboard_excluded_email("leafaronrutas123@gmail.com") is False
