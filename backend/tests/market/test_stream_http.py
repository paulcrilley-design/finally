"""GET /api/stream/prices over real HTTP, served by uvicorn."""

import asyncio
import json
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI

from app.market import PriceCache, create_stream_router
from app.market.simulator import SimulatorDataSource

from .helpers import wait_until


async def test_stream_serves_prices_and_server_stops_with_a_client_connected():
    """An open stream never ends by itself, so the server needs a graceful shutdown
    timeout. With one set, it must exit and still run the lifespan shutdown."""
    cache = PriceCache()
    source = SimulatorDataSource(cache, update_interval=0.05)
    shut_down = asyncio.Event()

    @asynccontextmanager
    async def lifespan(app):
        await source.start(["AAPL", "MSFT"])
        yield
        await source.stop()
        shut_down.set()

    app = FastAPI(lifespan=lifespan)
    app.include_router(create_stream_router(cache))
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="127.0.0.1",
            port=0,
            log_level="critical",
            ws="none",
            timeout_graceful_shutdown=1,
        )
    )
    serving = asyncio.create_task(server.serve())
    try:
        await wait_until(lambda: server.started)
        port = server.servers[0].sockets[0].getsockname()[1]
        url = f"http://127.0.0.1:{port}/api/stream/prices"
        async with asyncio.timeout(10):
            async with httpx.AsyncClient(trust_env=False) as client:
                async with client.stream("GET", url) as response:
                    assert response.status_code == 200
                    assert response.headers["content-type"].startswith("text/event-stream")
                    assert response.headers["cache-control"] == "no-cache"
                    assert response.headers["x-accel-buffering"] == "no"

                    lines = response.aiter_lines()
                    assert await anext(lines) == "retry: 1000"
                    assert await anext(lines) == ""
                    payload = json.loads((await anext(lines)).removeprefix("data: "))
                    assert set(payload) == {"AAPL", "MSFT"}
                    assert payload["AAPL"]["prev_close"] == 190.0

                    server.should_exit = True  # stop while the client is still connected
                    await asyncio.wait_for(asyncio.shield(serving), 5)
        assert shut_down.is_set()
    finally:
        server.should_exit = True
        server.force_exit = not serving.done()
        await serving
