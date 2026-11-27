"""FastAPI application: API, SSE stream and the static front end on one port."""

import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

import db
from app.errors import register_error_handlers
from app.llm import create_chat_router
from app.market import PriceCache, create_stream_router, start_market_data
from app.routes import health, portfolio, watchlist
from app.services.snapshots import run_snapshot_loop, snapshot_all

logger = logging.getLogger(__name__)

_DEFAULT_STATIC_DIR = Path(__file__).resolve().parents[2] / "frontend" / "out"
_ALL_METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db.init_db()
    app.state.market_source = await start_market_data(
        app.state.price_cache, sorted(db.all_tracked_tickers())
    )
    task = None
    try:
        snapshot_all(app.state)
        task = asyncio.create_task(run_snapshot_loop(app.state), name="snapshot-loop")
        yield
    finally:
        if task:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await app.state.market_source.stop()


async def _unknown_api_path() -> None:
    raise HTTPException(status_code=404)


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.state.price_cache = PriceCache()
    register_error_handlers(app)

    app.include_router(create_stream_router(app.state.price_cache))
    app.include_router(health.router)
    app.include_router(portfolio.router)
    app.include_router(watchlist.router)
    app.include_router(create_chat_router())
    # After the real routes, before static files, so a 404.html never answers an API call.
    for path in ("/api", "/api/{path:path}"):
        app.add_api_route(path, _unknown_api_path, methods=_ALL_METHODS, include_in_schema=False)

    static_dir = Path(os.environ.get("STATIC_DIR") or _DEFAULT_STATIC_DIR)
    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    else:
        logger.warning("Static directory %s not found; serving the API only", static_dir)
    return app


app = create_app()
