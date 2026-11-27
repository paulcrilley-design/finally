"""FastAPI app factory: database, market data, API routes and the static frontend."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from app.errors import ApiError, api_error_handler, invalid_request_handler
from app.market import PriceCache, create_stream_router, start_market_data
from app.routes import health_router, portfolio_router, watchlist_router
from db import (
    init_db,
    load_prices,
    record_snapshots,
    save_prices,
    tracked_tickers,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAVE_PRICES_EVERY = 5.0  # seconds
SNAPSHOT_EVERY = 30.0


def _save_current_prices(db_path: Path, cache: PriceCache) -> None:
    if not db_path.is_file():  # never recreate a database that has gone missing
        return
    save_prices(
        db_path,
        {t: (u.price, u.prev_close or u.price) for t, u in cache.get_all().items()},
    )


def _record_values(db_path: Path, cache: PriceCache) -> None:
    if db_path.is_file():
        record_snapshots(db_path, {t: u.price for t, u in cache.get_all().items()})


async def _repeat(
    every: float, job: Callable[[Path, PriceCache], None], db_path: Path, cache: PriceCache
) -> None:
    while True:
        await asyncio.sleep(every)
        try:
            await asyncio.to_thread(job, db_path, cache)
        except Exception:
            logger.exception("Background job %s failed", job.__name__)


def create_app(db_path: Path | None = None, static_dir: Path | None = None) -> FastAPI:
    """Build the app. Paths default to the environment, then the repository layout."""
    db_path = db_path or Path(
        os.environ.get("FINALLY_DB_PATH") or PROJECT_ROOT / "db" / "finally.db"
    )
    static_dir = static_dir or Path(
        os.environ.get("FINALLY_STATIC_DIR") or PROJECT_ROOT / "frontend" / "out"
    )
    cache = PriceCache()  # one per app, so tests share no state

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        init_db(db_path)
        source = await start_market_data(
            cache, tracked_tickers(db_path), resume=load_prices(db_path)
        )
        app.state.source = source
        app.state.tracking_lock = asyncio.Lock()
        _record_values(db_path, cache)  # so the value chart starts with a point
        jobs = [
            asyncio.create_task(_repeat(every, job, db_path, cache))
            for every, job in (
                (SAVE_PRICES_EVERY, _save_current_prices),
                (SNAPSHOT_EVERY, _record_values),
            )
        ]
        try:
            yield
        finally:
            for task in jobs:
                task.cancel()
            try:
                _save_current_prices(db_path, cache)
            except Exception:
                logger.exception("Could not save prices at shutdown")
            await source.stop()

    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.state.price_cache = cache
    app.state.db_path = db_path
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, invalid_request_handler)
    # API routes first: the static mount matches every other path.
    app.include_router(health_router)
    app.include_router(watchlist_router)
    app.include_router(portfolio_router)
    app.include_router(create_stream_router(cache))

    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False,
    )
    def api_not_found(path: str) -> None:
        """Unknown API paths get a JSON 404, not the frontend's HTML page."""
        raise HTTPException(status_code=404)

    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    else:
        logger.warning("No frontend build at %s: serving the API only", static_dir)
    return app
