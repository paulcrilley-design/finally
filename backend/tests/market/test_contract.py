"""Contract tests: behaviour every MarketDataSource must share."""

import asyncio

import pytest
from massive.rest.models import TickerSnapshot

from app.market import PriceCache
from app.market.massive_client import MassiveDataSource
from app.market.simulator import SimulatorDataSource
from tests.market.test_massive_source import FakeClient, snap


class EchoClient(FakeClient):
    """Returns a snapshot for whatever tickers are requested."""

    def get_snapshot_ticker(self, market_type, ticker, **kw):
        return snap(ticker, 100.0)

    def get_snapshot_all(self, market_type, tickers=None, **kw):
        return [
            TickerSnapshot.from_dict(
                {"ticker": t, "lastTrade": {"p": 100.0, "t": 1_764_080_900_000_000_000}}
            )
            for t in tickers
        ]


def build(kind, cache):
    if kind == "simulator":
        return SimulatorDataSource(cache, update_interval=0.02)
    return MassiveDataSource("k", cache, poll_interval=0.02, client=EchoClient())


@pytest.fixture(params=["simulator", "massive"])
async def source(request):
    cache = PriceCache()
    src = build(request.param, cache)
    src.cache = cache
    yield src
    await src.stop()


async def test_start_populates_cache(source):
    await source.start(["AAPL", "MSFT"])
    assert source.cache.get_price("AAPL") and source.cache.get_price("MSFT")


async def test_start_normalises_and_drops_invalid_symbols(source, caplog):
    await source.start([" aapl ", "AAPL", "", "bad symbol!", "msft"])
    assert source.get_tickers() == ["AAPL", "MSFT"]
    assert set(source.cache.get_all()) == {"AAPL", "MSFT"}
    assert "BAD SYMBOL!" in caplog.text


async def test_add_remove_are_idempotent_and_normalised(source):
    await source.start(["AAPL"])
    await source.add_ticker(" nvda ")
    await source.add_ticker("NVDA")
    assert source.get_tickers().count("NVDA") == 1
    for _ in range(100):
        if source.cache.get("NVDA"):
            break
        await asyncio.sleep(0.05)
    assert source.cache.get("NVDA") is not None
    await source.remove_ticker("nvda")
    await source.remove_ticker("NVDA")
    assert "NVDA" not in source.get_tickers() and source.cache.get("NVDA") is None


async def test_stop_twice_is_safe_and_status_shape(source):
    await source.start(["AAPL"])
    assert await source.validate_ticker("AAPL") is True
    assert await source.validate_ticker("1bad!") is False
    await source.stop()
    await source.stop()
    assert {"mode", "degraded", "tickers"} <= set(source.status())
