"""A real server: an open price stream blocks neither other requests nor shutdown."""

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
import uvicorn

from app.main import create_app

from .market.helpers import wait_until

pytestmark = pytest.mark.usefixtures("app_env")


@asynccontextmanager
async def serve(
    static_dir: Path, graceful_timeout: int
) -> AsyncIterator[tuple[uvicorn.Server, asyncio.Task, str, asyncio.Event]]:
    """Run the app on a free port. The event is set when lifespan stops the source."""
    app = create_app(static_dir=static_dir)
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=0,
            log_level="critical",
            ws="none",
            timeout_graceful_shutdown=graceful_timeout,
        )
    )
    serving = asyncio.create_task(server.serve())
    try:
        await wait_until(lambda: server.started)
        stopped = asyncio.Event()
        original_stop = app.state.source.stop

        async def recording_stop() -> None:
            await original_stop()
            stopped.set()

        app.state.source.stop = recording_stop
        base = f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}"
        yield server, serving, base, stopped
    finally:
        server.should_exit = True
        server.force_exit = not serving.done()
        await serving


async def test_open_stream_server_stays_responsive_and_stops_cleanly(static_dir: Path):
    async with serve(static_dir, graceful_timeout=1) as (server, serving, base, stopped):
        async with asyncio.timeout(10):
            async with httpx.AsyncClient(base_url=base, trust_env=False) as client:
                async with client.stream("GET", "/api/stream/prices") as response:
                    lines = response.aiter_lines()
                    assert await anext(lines) == "retry: 1000"

                    for path in ("/", "/api/watchlist", "/api/health"):
                        assert (await client.get(path)).status_code == 200, path

                    server.should_exit = True  # stop while the client is still connected
                    await asyncio.wait_for(asyncio.shield(serving), 5)
                    assert stopped.is_set()


async def test_idle_server_stops_without_waiting(static_dir: Path):
    async with serve(static_dir, graceful_timeout=3) as (server, serving, base, stopped):
        async with httpx.AsyncClient(base_url=base, trust_env=False) as client:
            assert (await client.get("/api/health")).status_code == 200

        started = time.monotonic()
        server.should_exit = True
        await asyncio.wait_for(asyncio.shield(serving), 5)
        assert time.monotonic() - started < 2.5
        assert stopped.is_set()
