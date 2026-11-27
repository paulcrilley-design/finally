"""SQLite schema, seed data and queries. Stdlib sqlite3 only."""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Iterator
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
