"""The assembled app: database, price stream, API 404 and static frontend."""

import asyncio
import json
from pathlib import Path

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from app.identity import get_current_user
from app.main import create_app
from db import connect

from .market.helpers import wait_until

pytestmark = pytest.mark.usefixtures("app_env")

SEEDED = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]
PRICE_KEYS = (
    "price",
    "previous_price",
    "timestamp",
    "change",
    "change_percent",
    "direction",
    "prev_close",
    "day_change",
    "day_change_percent",
)


# Not autouse: tests/market/test_factory.py selects sources through the same variables.
@pytest.fixture
def app_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "db" / "finally.db"
    monkeypatch.setenv("MARKET_FORCE_SIMULATOR", "true")
    monkeypatch.setenv("FINALLY_DB_PATH", str(db_path))
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.delenv("FINALLY_STATIC_DIR", raising=False)
    return db_path


@pytest.fixture
def static_dir(tmp_path: Path) -> Path:
    out = tmp_path / "out"
    out.mkdir()
    (out / "index.html").write_text("<h1>FinAlly stub</h1>")
    return out


async def test_walking_skeleton_end_to_end(app_env: Path, static_dir: Path):
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(static_dir=static_dir),
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
        base = f"http://127.0.0.1:{server.servers[0].sockets[0].getsockname()[1]}"
        async with asyncio.timeout(10):
            async with httpx.AsyncClient(base_url=base, trust_env=False) as client:
                page = await client.get("/")
                assert page.status_code == 200
                assert "FinAlly stub" in page.text

                watchlist = (await client.get("/api/watchlist")).json()["watchlist"]
                assert [item["ticker"] for item in watchlist] == SEEDED
                assert all(item["price"] is not None for item in watchlist)

                async with client.stream("GET", "/api/stream/prices") as response:
                    assert response.status_code == 200
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            break
                    prices = json.loads(line.removeprefix("data: "))
                    assert set(prices) == set(SEEDED)
                    assert all(entry["price"] is not None for entry in prices.values())
                    assert app_env.is_file()

                    server.should_exit = True  # stop while the client is still connected
                    await asyncio.wait_for(asyncio.shield(serving), 5)
    finally:
        server.should_exit = True
        server.force_exit = not serving.done()
        await serving


@pytest.mark.parametrize("method", ["get", "post"])
def test_unknown_api_path_is_json_404(static_dir: Path, method: str):
    with TestClient(create_app(static_dir=static_dir)) as client:
        response = getattr(client, method)("/api/no-such-endpoint")
        assert response.status_code == 404
        assert response.json() == {"detail": "Not Found"}


def test_ticker_without_a_price_has_null_price_fields(app_env: Path, static_dir: Path):
    with TestClient(create_app(static_dir=static_dir)) as client:
        with connect(app_env) as conn:  # after startup, so no source tracks it
            conn.execute(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                ("zzzz", "default", "ZZZZ", "9999-01-01T00:00:00+00:00"),
            )
        item = client.get("/api/watchlist").json()["watchlist"][-1]
        assert item == {"ticker": "ZZZZ", **dict.fromkeys(PRICE_KEYS)}


def test_overridden_user_gets_empty_watchlist(static_dir: Path):
    app = create_app(static_dir=static_dir)
    app.dependency_overrides[get_current_user] = lambda: "nobody"
    with TestClient(app) as client:
        assert client.get("/api/watchlist").json() == {"watchlist": []}


def test_missing_static_dir_serves_the_api_only(tmp_path: Path):
    with TestClient(create_app(static_dir=tmp_path / "missing")) as client:
        response = client.get("/api/no-such-endpoint")
        assert response.status_code == 404
        assert response.json() == {"detail": "Not Found"}
        assert client.get("/api/watchlist").status_code == 200
