import sqlite3
import uuid
from datetime import UTC, datetime, timedelta

import pytest

import db


@pytest.fixture(autouse=True)
def database(tmp_path, monkeypatch):
    """A fresh seeded database in a temporary directory."""
    path = tmp_path / "data" / "finally.db"
    monkeypatch.setenv("DB_PATH", str(path))
    db.init_db()
    return path


@pytest.fixture
def execute(database):
    """Run raw SQL against the test database."""

    def run(sql, params=()):
        conn = sqlite3.connect(database)
        try:
            with conn:
                return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    return run


@pytest.fixture
def other_user(execute):
    execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        ("other", 500.0, datetime.now(UTC).isoformat()),
    )
    return "other"


@pytest.fixture
def insert_snapshot(execute):
    """Insert a snapshot recorded `age` before now."""

    def insert(total_value, age: timedelta, user_id="default"):
        recorded_at = (datetime.now(UTC) - age).isoformat(timespec="microseconds")
        execute(
            "INSERT INTO portfolio_snapshots VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, total_value, recorded_at),
        )

    return insert
