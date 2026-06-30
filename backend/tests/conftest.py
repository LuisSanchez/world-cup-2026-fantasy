"""Shared pytest fixtures. External I/O and DB sessions are mocked in unit tests."""

import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Avoid loading production .env secrets during tests
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("SUPER_ADMIN_EMAIL", "admin@localhost.dev")
os.environ.setdefault("ADMIN_EMAILS", "leafaronrutas123@gmail.com,luis.sanchezm86@gmail.com")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def sample_match():
    return SimpleNamespace(
        id=1,
        match_number=1,
        home_team="México",
        away_team="Sudáfrica",
        home_flag="mx",
        away_flag="za",
        kickoff=datetime(2026, 6, 11, 19, 0, 0),
        stage="group",
        group_name="",
        home_score=None,
        away_score=None,
        is_finished=False,
        is_placeholder=False,
    )


@pytest.fixture
def finished_match():
    return SimpleNamespace(
        id=2,
        match_number=2,
        home_team="Brasil",
        away_team="Haití",
        home_flag="br",
        away_flag="ht",
        kickoff=datetime(2026, 6, 20, 19, 0, 0),
        stage="group",
        group_name="",
        home_score=3,
        away_score=0,
        is_finished=True,
        is_placeholder=False,
    )
