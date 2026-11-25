"""SSE streaming endpoint for live price updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .cache import PriceCache

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 15.0  # comment line so proxies do not drop an idle connection


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Build a fresh router per call (safe to call twice, e.g. in tests)."""
    router = APIRouter(prefix="/api/stream", tags=["streaming"])

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return router


async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
    heartbeat: float = HEARTBEAT_SECONDS,
) -> AsyncGenerator[str, None]:
    """Yield `data:` events when the cache changed, and `: keepalive` when idle."""
    yield "retry: 1000\n\n"

    last_version = -1
    idle = 0.0
    client = request.client.host if request.client else "unknown"
    logger.info("SSE client connected: %s", client)

    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected: %s", client)
                break

            version = price_cache.version
            if version != last_version:
                last_version = version
                prices = price_cache.get_all()
                # An empty dict is still sent, so clients drop tickers that were removed.
                yield f"data: {json.dumps({t: u.to_dict() for t, u in prices.items()})}\n\n"
                idle = 0.0
            elif idle >= heartbeat:
                yield ": keepalive\n\n"
                idle = 0.0

            await asyncio.sleep(interval)
            idle += interval
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled for: %s", client)
