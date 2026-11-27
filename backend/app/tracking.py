"""Keep the market source pricing exactly what is watched or held."""

from __future__ import annotations

from fastapi.concurrency import run_in_threadpool
from starlette.datastructures import State

from app.market import reconcile_tickers
from db import tracked_tickers


async def sync_tracked_tickers(state: State) -> None:
    # The lock stops an older list from being applied after a newer one.
    async with state.tracking_lock:
        wanted = await run_in_threadpool(tracked_tickers, state.db_path)
        await reconcile_tickers(state.source, wanted)
