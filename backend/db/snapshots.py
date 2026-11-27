"""Portfolio value over time: one row per user per snapshot."""

from __future__ import annotations

import sqlite3
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from .database import connect

KEEP_FOR = timedelta(days=7)
MAX_POINTS = 500


def _stamp(moment: datetime) -> str:
    return moment.isoformat(timespec="microseconds")


def add_snapshot(conn: sqlite3.Connection, user_id: str, prices: Mapping[str, float]) -> None:
    """Record the user's total value, unless any held price is unknown (never substituted).

    Runs inside the caller's transaction.
    """
    profile = conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)
    ).fetchone()
    if profile is None:
        return
    cent = Decimal("0.01")
    total = Decimal(str(profile["cash_balance"])).quantize(cent, ROUND_HALF_UP)
    held = conn.execute("SELECT ticker, quantity FROM positions WHERE user_id = ?", (user_id,))
    for row in held.fetchall():
        price = prices.get(row["ticker"])
        if price is None:
            return
        value = Decimal(str(row["quantity"])) * Decimal(str(price))
        total += value.quantize(cent, ROUND_HALF_UP)
    conn.execute(
        "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)"
        " VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), user_id, float(total), _stamp(datetime.now(UTC))),
    )


def record_snapshots(path: Path, prices: Mapping[str, float]) -> None:
    """Snapshot every user and drop rows past retention."""
    with connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        for row in conn.execute("SELECT id FROM users_profile").fetchall():
            add_snapshot(conn, row["id"], prices)
        conn.execute(
            "DELETE FROM portfolio_snapshots WHERE recorded_at < ?",
            (_stamp(datetime.now(UTC) - KEEP_FOR),),
        )


def value_history(path: Path, user_id: str, limit: int = MAX_POINTS) -> list[dict]:
    """Oldest first, evenly thinned to `limit` points, keeping the first and the latest."""
    with connect(path) as conn:
        rows = conn.execute(
            "SELECT recorded_at, total_value FROM portfolio_snapshots"
            " WHERE user_id = ? ORDER BY recorded_at, rowid",
            (user_id,),
        ).fetchall()
    if len(rows) > limit:
        last = len(rows) - 1
        rows = [rows[round(i * last / (limit - 1))] for i in range(limit)]
    return [dict(row) for row in rows]
