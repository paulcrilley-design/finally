from pathlib import Path

import db
from db.connection import DEFAULT_DB_PATH, db_path

SEEDED = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]


def test_seed_data(database):
    assert database.exists()
    assert db.list_user_ids() == ["default"]
    assert db.get_cash("default") == 10000.0
    assert db.list_watchlist("default") == SEEDED
    assert db.list_positions("default") == []
    assert db.list_trades("default") == []
    assert db.list_snapshots("default") == []
    assert db.list_chat_messages("default") == []


def test_init_is_idempotent_and_keeps_changes():
    db.remove_watchlist("default", "AAPL")
    db.apply_trade("default", "MSFT", "buy", 1, 100)
    db.init_db()
    db.init_db()
    assert db.list_user_ids() == ["default"]
    assert db.list_watchlist("default") == SEEDED[1:]
    assert db.get_cash("default") == 9900.0


def test_init_recreates_missing_table(execute):
    execute("DROP TABLE trades")
    db.init_db()
    assert db.list_trades("default") == []


def test_indexes_exist(execute):
    names = {row[0] for row in execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
    assert {"idx_trades_user", "idx_snapshots_user", "idx_chat_user"} <= names


def test_default_path(monkeypatch):
    monkeypatch.delenv("DB_PATH")
    root = Path(__file__).resolve().parents[3]
    assert db_path() == DEFAULT_DB_PATH == root / "db" / "finally.db"
