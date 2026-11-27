"""Schema creation and default seed data."""

import uuid

from .connection import db_path, transaction, utc_now

DEFAULT_USER_ID = "default"
DEFAULT_CASH = 10000.0
DEFAULT_TICKERS = (
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "NVDA",
    "META",
    "JPM",
    "V",
    "NFLX",
)

SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS users_profile (
        id TEXT PRIMARY KEY DEFAULT 'default',
        cash_balance REAL NOT NULL DEFAULT 10000.0,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS watchlist (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'default',
        ticker TEXT NOT NULL,
        added_at TEXT NOT NULL,
        UNIQUE (user_id, ticker)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS positions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'default',
        ticker TEXT NOT NULL,
        quantity REAL NOT NULL,
        avg_cost REAL NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (user_id, ticker)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trades (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'default',
        ticker TEXT NOT NULL,
        side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        executed_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'default',
        total_value REAL NOT NULL,
        recorded_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL DEFAULT 'default',
        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
        content TEXT NOT NULL,
        actions TEXT,
        created_at TEXT NOT NULL
    )
    """,
    # watchlist and positions are already indexed on user_id by their UNIQUE constraints.
    "CREATE INDEX IF NOT EXISTS idx_trades_user ON trades (user_id, executed_at)",
    "CREATE INDEX IF NOT EXISTS idx_snapshots_user ON portfolio_snapshots (user_id, recorded_at)",
    "CREATE INDEX IF NOT EXISTS idx_chat_user ON chat_messages (user_id, created_at)",
)


def init_db() -> None:
    """Create any missing tables and indexes, and seed defaults if there are no users."""
    db_path().parent.mkdir(parents=True, exist_ok=True)
    with transaction() as conn:
        for statement in SCHEMA:
            conn.execute(statement)
        if conn.execute("SELECT 1 FROM users_profile LIMIT 1").fetchone():
            return
        now = utc_now()
        conn.execute(
            "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            (DEFAULT_USER_ID, DEFAULT_CASH, now),
        )
        conn.executemany(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            [(str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now) for ticker in DEFAULT_TICKERS],
        )
