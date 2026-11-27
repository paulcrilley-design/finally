"""Watchlists, and the set of tickers that need market data."""

import uuid

from .connection import connect, utc_now


def list_watchlist(user_id: str) -> list[str]:
    """Tickers in the order they were added."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid", (user_id,)
        ).fetchall()
    return [row["ticker"] for row in rows]


def add_watchlist(user_id: str, ticker: str) -> bool:
    """Add a ticker. Returns False if it is already there."""
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (user_id, ticker) DO NOTHING",
            (str(uuid.uuid4()), user_id, ticker, utc_now()),
        )
        return cursor.rowcount == 1


def remove_watchlist(user_id: str, ticker: str) -> bool:
    """Remove a ticker. Returns False if it was not there."""
    with connect() as conn:
        cursor = conn.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker)
        )
        return cursor.rowcount == 1


def all_tracked_tickers() -> set[str]:
    """Every ticker on any user's watchlist or held in any user's positions."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT ticker FROM watchlist UNION SELECT ticker FROM positions"
        ).fetchall()
    return {row["ticker"] for row in rows}
