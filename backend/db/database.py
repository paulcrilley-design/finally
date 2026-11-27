"""SQLite schema, seed data and queries. Stdlib sqlite3 only."""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

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

# There is no migration step: every table exists from the first run.
SCHEMA = """
CREATE TABLE IF NOT EXISTS users_profile (
  id TEXT PRIMARY KEY DEFAULT 'default',
  cash_balance REAL NOT NULL DEFAULT 10000.0,
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS watchlist (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default',
  ticker TEXT NOT NULL, added_at TEXT NOT NULL, UNIQUE (user_id, ticker));
CREATE TABLE IF NOT EXISTS positions (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default', ticker TEXT NOT NULL,
  quantity REAL NOT NULL, avg_cost REAL NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE (user_id, ticker));
CREATE TABLE IF NOT EXISTS trades (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default', ticker TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
  quantity REAL NOT NULL, price REAL NOT NULL, executed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default',
  total_value REAL NOT NULL, recorded_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default',
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL, actions TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS last_prices (
  ticker TEXT PRIMARY KEY, price REAL NOT NULL, prev_close REAL NOT NULL, saved_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist (user_id);
CREATE INDEX IF NOT EXISTS idx_positions_user ON positions (user_id);
CREATE INDEX IF NOT EXISTS idx_trades_user ON trades (user_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_user_time ON portfolio_snapshots (user_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_chat_user_time ON chat_messages (user_id, created_at);
"""


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    """Open a connection, commit or roll back the body, then close."""
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        with conn:  # commits or rolls back, but does not close
            yield conn
    finally:
        conn.close()


def seed(conn: sqlite3.Connection) -> None:
    """Insert the default user and watchlist once, in one transaction.

    Gated on the profile row only, so tickers a user removes are never re-added.
    """
    # Take the write lock before checking, so two starts cannot both pass the check.
    conn.execute("BEGIN IMMEDIATE")
    profile = conn.execute("SELECT 1 FROM users_profile WHERE id = ?", (DEFAULT_USER_ID,))
    if profile.fetchone() is not None:
        return
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (DEFAULT_USER_ID, DEFAULT_CASH, now),
    )
    conn.executemany(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
        [(str(uuid.uuid4()), DEFAULT_USER_ID, ticker, now) for ticker in DEFAULT_TICKERS],
    )


def init_db(path: Path) -> None:
    """Create any missing tables and seed a new database."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        seed(conn)


def tracked_tickers(path: Path) -> list[str]:
    """Every ticker watched or held by any user (market data is global)."""
    with connect(path) as conn:
        rows = conn.execute("SELECT ticker FROM watchlist UNION SELECT ticker FROM positions")
        return [row["ticker"] for row in rows]


def list_watchlist(path: Path, user_id: str) -> list[str]:
    """One user's watched tickers, in the order they were added."""
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid",
            (user_id,),
        )
        return [row["ticker"] for row in rows]


def is_healthy(path: Path) -> bool:
    """Whether the database can be read. Opens read-only, so it never creates a file."""
    try:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            conn.execute("SELECT 1 FROM users_profile LIMIT 1").fetchone()
        finally:
            conn.close()
    except sqlite3.Error:
        return False
    return True


def add_to_watchlist(path: Path, user_id: str, ticker: str) -> bool:
    """False if the user already watches the ticker."""
    with connect(path) as conn:
        added = conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (user_id, ticker) DO NOTHING",
            (str(uuid.uuid4()), user_id, ticker, datetime.now(UTC).isoformat()),
        )
        return added.rowcount == 1


def remove_from_watchlist(path: Path, user_id: str, ticker: str) -> bool:
    """False if the user does not watch the ticker."""
    with connect(path) as conn:
        removed = conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
        )
        return removed.rowcount == 1


UPSERT_PRICE = (
    "INSERT INTO last_prices (ticker, price, prev_close, saved_at) VALUES (?, ?, ?, ?)"
    " ON CONFLICT (ticker) DO UPDATE SET price = excluded.price,"
    " prev_close = excluded.prev_close, saved_at = excluded.saved_at"
)


def save_prices(path: Path, prices: Mapping[str, tuple[float, float]]) -> None:
    """Remember {ticker: (price, previous close)} so a restart can continue from it."""
    now = datetime.now(UTC).isoformat()
    with connect(path) as conn:
        conn.executemany(
            UPSERT_PRICE,
            [(ticker, price, prev, now) for ticker, (price, prev) in prices.items()],
        )


def load_prices(path: Path) -> dict[str, tuple[float, float]]:
    with connect(path) as conn:
        rows = conn.execute("SELECT ticker, price, prev_close FROM last_prices")
        return {row["ticker"]: (row["price"], row["prev_close"]) for row in rows}
