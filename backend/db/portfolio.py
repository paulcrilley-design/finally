"""Positions, trades and portfolio value snapshots."""

import math
import uuid
from datetime import UTC, datetime, timedelta

from .connection import connect, transaction, utc_now
from .errors import InsufficientCash, InsufficientShares

POSITION_COLUMNS = "ticker, quantity, avg_cost, updated_at"
SNAPSHOT_DAYS = 7


def list_positions(user_id: str) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            f"SELECT {POSITION_COLUMNS} FROM positions WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_position(user_id: str, ticker: str) -> dict | None:
    with connect() as conn:
        row = conn.execute(
            f"SELECT {POSITION_COLUMNS} FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
    return dict(row) if row else None


def apply_trade(user_id: str, ticker: str, side: str, quantity: float, price: float) -> dict:
    """Execute a trade atomically: check funds or shares, update cash and position, log it.

    Raises InsufficientCash or InsufficientShares, changing nothing. Raises ValueError for
    a bad side, quantity or price, and KeyError for an unknown user.
    """
    if side not in ("buy", "sell"):
        raise ValueError(f"Invalid side: {side!r}")
    if not math.isfinite(quantity) or round(quantity, 4) <= 0:
        raise ValueError(f"Invalid quantity: {quantity!r}")
    if not math.isfinite(price) or price <= 0:
        raise ValueError(f"Invalid price: {price!r}")
    quantity = round(quantity, 4)
    value = round(quantity * price, 2)

    with transaction() as conn:
        user = conn.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
        ).fetchone()
        if user is None:
            raise KeyError(user_id)
        cash = user["cash_balance"]
        position = conn.execute(
            "SELECT quantity, avg_cost FROM positions WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
        held, avg_cost = (position["quantity"], position["avg_cost"]) if position else (0.0, 0.0)

        if side == "buy":
            if value > cash:
                raise InsufficientCash(f"Need ${value:,.2f} but only ${cash:,.2f} is available.")
            new_quantity = round(held + quantity, 4)
            avg_cost = (held * avg_cost + quantity * price) / new_quantity
            cash = round(cash - value, 2)
        else:
            if quantity > held:
                raise InsufficientShares(f"Cannot sell {quantity:g} {ticker}: you hold {held:g}.")
            new_quantity = round(held - quantity, 4)
            cash = round(cash + value, 2)

        executed_at = utc_now()
        conn.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (cash, user_id))
        if new_quantity <= 0:
            conn.execute(
                "DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker)
            )
        else:
            conn.execute(
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT (user_id, ticker) DO UPDATE SET quantity = excluded.quantity, "
                "avg_cost = excluded.avg_cost, updated_at = excluded.updated_at",
                (str(uuid.uuid4()), user_id, ticker, new_quantity, avg_cost, executed_at),
            )
        trade = {
            "id": str(uuid.uuid4()),
            "ticker": ticker,
            "side": side,
            "quantity": quantity,
            "price": price,
            "executed_at": executed_at,
        }
        conn.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
            "VALUES (:id, :user_id, :ticker, :side, :quantity, :price, :executed_at)",
            {**trade, "user_id": user_id},
        )
    return trade


def list_trades(user_id: str, limit: int = 100) -> list[dict]:
    """Newest first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, ticker, side, quantity, price, executed_at FROM trades "
            "WHERE user_id = ? ORDER BY executed_at DESC, rowid DESC LIMIT ?",
            (user_id, max(limit, 0)),
        ).fetchall()
    return [dict(row) for row in rows]


def _cutoff(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat(timespec="microseconds")


def add_snapshot(user_id: str, total_value: float) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) "
            "VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, total_value, utc_now()),
        )


def list_snapshots(user_id: str, limit: int = 500) -> list[dict]:
    """The last 7 days, oldest first.

    More than `limit` rows are downsampled evenly, keeping the first and the newest.
    A limit of 1 returns only the newest.
    """
    with connect() as conn:
        rows = conn.execute(
            "SELECT total_value, recorded_at FROM portfolio_snapshots "
            "WHERE user_id = ? AND recorded_at >= ? ORDER BY recorded_at, rowid",
            (user_id, _cutoff(SNAPSHOT_DAYS)),
        ).fetchall()
    if limit <= 0:
        return []
    if len(rows) > limit:
        if limit == 1:
            rows = rows[-1:]
        else:
            last = len(rows) - 1
            rows = [rows[round(i * last / (limit - 1))] for i in range(limit)]
    return [dict(row) for row in rows]


def prune_snapshots(user_id: str, days: int = SNAPSHOT_DAYS) -> None:
    """Delete this user's snapshots older than `days`."""
    with connect() as conn:
        conn.execute(
            "DELETE FROM portfolio_snapshots WHERE user_id = ? AND recorded_at < ?",
            (user_id, _cutoff(days)),
        )
