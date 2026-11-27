"""Portfolio value snapshots for the P&L chart."""

import asyncio
import logging

import db

logger = logging.getLogger(__name__)

SNAPSHOT_SECONDS = 30.0


def take_snapshot(state, user_id: str) -> None:
    """Record the user's total value. Skipped if any position has no price."""
    from app.services.portfolio import get_portfolio  # portfolio imports this module

    portfolio = get_portfolio(state, user_id)
    if any(p["current_price"] is None for p in portfolio["positions"]):
        return
    db.add_snapshot(user_id, portfolio["total_value"])


def snapshot_all(state) -> None:
    """Snapshot and prune every user. One user's failure does not stop the others."""
    for user_id in db.list_user_ids():
        try:
            take_snapshot(state, user_id)
            db.prune_snapshots(user_id)
        except Exception:
            logger.exception("Portfolio snapshot failed")


async def run_snapshot_loop(state, interval: float = SNAPSHOT_SECONDS) -> None:
    while True:
        await asyncio.sleep(interval)
        try:
            snapshot_all(state)
        except Exception:
            logger.exception("Portfolio snapshot run failed")
