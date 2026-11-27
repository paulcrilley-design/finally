"""Database guarantees: seed once, survive restarts, stay per user."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from db import connect, database, init_db, list_watchlist, tracked_tickers

SEEDED = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]
TABLES = {
    "users_profile",
    "watchlist",
    "positions",
    "trades",
    "portfolio_snapshots",
    "chat_messages",
}
# Table name to the other required columns and a valid value for each.
USER_OWNED = {
    "watchlist": {"ticker": "AAPL", "added_at": "t"},
    "positions": {"ticker": "AAPL", "quantity": 1.0, "avg_cost": 1.0, "updated_at": "t"},
    "trades": {
        "ticker": "AAPL",
        "side": "buy",
        "quantity": 1.0,
        "price": 1.0,
        "executed_at": "t",
    },
    "portfolio_snapshots": {"total_value": 1.0, "recorded_at": "t"},
    "chat_messages": {"role": "user", "content": "hi", "created_at": "t"},
}


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / "finally.db"
    init_db(path)
    return path


def _query(path: Path, sql: str) -> list[tuple]:
    with connect(path) as conn:
        return [tuple(row) for row in conn.execute(sql)]


def _execute(path: Path, sql: str, values: tuple = ()) -> None:
    with connect(path) as conn:
        conn.execute(sql, values)


def _insert(path: Path, table: str, row: dict) -> None:
    columns = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    _execute(path, f"INSERT INTO {table} ({columns}) VALUES ({marks})", tuple(row.values()))


def _snapshot(path: Path) -> dict[str, list[tuple]]:
    return {table: _query(path, f"SELECT * FROM {table} ORDER BY rowid") for table in TABLES}


def test_fresh_database_has_six_tables_and_seed(db_path: Path):
    tables = _query(db_path, "SELECT name FROM sqlite_master WHERE type = 'table'")
    assert {name for (name,) in tables} == TABLES
    assert _query(db_path, "SELECT id, cash_balance FROM users_profile") == [("default", 10000.0)]
    rows = _query(db_path, "SELECT user_id, ticker FROM watchlist ORDER BY rowid")
    assert rows == [("default", ticker) for ticker in SEEDED]


def test_init_creates_missing_parent_directory(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "finally.db"
    init_db(path)
    assert path.is_file()


def test_user_owned_tables_require_user_id(db_path: Path):
    for table, values in USER_OWNED.items():
        columns = {row[1]: row[3] for row in _query(db_path, f"PRAGMA table_info({table})")}
        assert columns["user_id"] == 1, f"{table}.user_id must be NOT NULL"
        with pytest.raises(sqlite3.IntegrityError, match="user_id"):
            _insert(db_path, table, {"id": "x", "user_id": None, **values})


def test_second_init_changes_nothing(db_path: Path):
    _execute(db_path, "UPDATE users_profile SET cash_balance = ?", (1234.5,))
    before = _snapshot(db_path)
    init_db(db_path)
    assert _snapshot(db_path) == before


def test_removed_tickers_stay_removed(db_path: Path):
    _execute(db_path, "DELETE FROM watchlist WHERE ticker = ?", ("AAPL",))
    init_db(db_path)
    assert list_watchlist(db_path, "default") == SEEDED[1:]

    _execute(db_path, "DELETE FROM watchlist")
    init_db(db_path)
    assert list_watchlist(db_path, "default") == []


def test_interrupted_seed_leaves_no_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "finally.db"
    with monkeypatch.context() as patch:
        patch.setattr(database, "DEFAULT_TICKERS", ("AAPL", None))
        with pytest.raises(sqlite3.IntegrityError):
            init_db(path)
    assert _query(path, "SELECT * FROM users_profile") == []
    assert _query(path, "SELECT * FROM watchlist") == []

    init_db(path)
    assert list_watchlist(path, "default") == SEEDED


@pytest.mark.parametrize("attempt", range(20))  # a race needs several chances to appear
def test_concurrent_init_seeds_once(tmp_path: Path, attempt: int):
    path = tmp_path / "finally.db"
    start = Barrier(8)

    def run() -> None:
        start.wait()
        init_db(path)

    with ThreadPoolExecutor(max_workers=8) as pool:
        for future in [pool.submit(run) for _ in range(8)]:
            future.result()

    assert len(_query(path, "SELECT * FROM users_profile")) == 1
    assert list_watchlist(path, "default") == SEEDED


def test_users_keep_separate_rows_and_union_is_deduplicated(db_path: Path):
    other = {"user_id": "other", **USER_OWNED["watchlist"]}
    _insert(db_path, "watchlist", {"id": "w1", **other})
    with pytest.raises(sqlite3.IntegrityError):
        _insert(db_path, "watchlist", {"id": "w2", **other})
    held = {**USER_OWNED["positions"], "ticker": "PYPL"}
    _insert(db_path, "positions", {"id": "p1", "user_id": "other", **held})

    assert list_watchlist(db_path, "other") == ["AAPL"]
    assert list_watchlist(db_path, "default") == SEEDED
    tracked = tracked_tickers(db_path)
    assert tracked.count("AAPL") == 1
    assert "PYPL" in tracked


def test_unknown_user_gets_empty_watchlist(db_path: Path):
    assert list_watchlist(db_path, "nobody") == []


def test_order_is_stable_for_equal_timestamps(db_path: Path):
    _execute(db_path, "UPDATE watchlist SET added_at = ?", ("2026-01-01T00:00:00+00:00",))
    for _ in range(3):
        assert list_watchlist(db_path, "default") == SEEDED
