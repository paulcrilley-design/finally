"""GET /api/health: whether the app, its database and market data are working."""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from db import is_healthy

STALE_AFTER_SECONDS = 10.0  # the simulator writes twice a second

router = APIRouter(prefix="/api", tags=["system"])


def market_state(source_status: dict, newest_timestamp: float | None, now: float) -> str:
    """'ok' or 'degraded'. Only the simulator is judged on price age."""
    if source_status["degraded"]:
        return "degraded"
    if source_status["mode"] == "simulator" and source_status["tickers"] > 0:
        if newest_timestamp is None or now - newest_timestamp > STALE_AFTER_SECONDS:
            return "degraded"
    return "ok"


@router.get("/health")
def health(request: Request) -> dict:
    """Always 200. Never returns the degraded reason, a path or exception text."""
    state = request.app.state
    source_status = state.source.status()
    prices = state.price_cache.get_all().values()
    newest = max((update.timestamp for update in prices), default=None)
    market = market_state(source_status, newest, time.time())
    healthy = market == "ok" and is_healthy(state.db_path)
    return {
        "status": "ok" if healthy else "degraded",
        "market_data": {
            "mode": source_status["mode"],
            "status": market,
            "tickers": source_status["tickers"],
        },
    }
