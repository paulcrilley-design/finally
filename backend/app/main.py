"""FastAPI app factory: database, market data, API routes and the static frontend."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.market import PriceCache, create_stream_router, start_market_data
from db.database import init_db, tracked_tickers

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
        source = await start_market_data(cache, tracked_tickers(db_path))
        app.state.source = source
        try:
            yield
        finally:
            await source.stop()

    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.state.price_cache = cache
    app.state.db_path = db_path
    # API routes first: the static mount matches every other path.
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
