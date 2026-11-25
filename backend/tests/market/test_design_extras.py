"""Tests for the design additions: prev_close, seeded simulator, SSE, factory fallback."""

import asyncio
import json
import math

import numpy as np
import pytest
from massive.exceptions import AuthError

from app.market import PriceCache, create_market_data_source, start_market_data
from app.market.massive_client import MassiveDataSource, make_client
from app.market.simulator import GBMSimulator, SimulatorDataSource
from app.market.stream import _generate_events


class TestPrevClose:
    def test_day_change_and_stickiness(self):
        c = PriceCache()
        c.update("AAPL", 101.0, prev_close=100.0)
        u = c.update("AAPL", 102.0)  # prev_close omitted: kept
        assert u.prev_close == 100.0 and u.day_change == 2.0 and u.day_change_percent == 2.0
        assert u.to_dict()["day_change_percent"] == 2.0

    def test_unknown_baseline_is_none_not_zero(self):
        u = PriceCache().update("AAPL", 101.0)
        assert u.day_change is None and u.to_dict()["prev_close"] is None


class TestSimulator:
    def test_same_seed_same_series(self):
        a, b = GBMSimulator(["AAPL", "MSFT"], seed=7), GBMSimulator(["AAPL", "MSFT"], seed=7)
        assert [a.step() for _ in range(50)] == [b.step() for _ in range(50)]

    def test_volatility_calibration(self):
        sim = GBMSimulator(["AAPL"], event_probability=0.0, seed=1)
        px = [sim.get_price("AAPL")] + [sim.step()["AAPL"] for _ in range(20000)]
        # use unrounded internal path via many steps: 2dp rounding adds noise, so compare loosely
        r = np.diff(np.log(px))
        sigma_hat = r.std() / math.sqrt(GBMSimulator.DEFAULT_DT)
        assert sigma_hat == pytest.approx(0.22, rel=0.15)

    def test_correlation_tech_vs_cross_sector(self):
        sim = GBMSimulator(["AAPL", "MSFT", "JPM"], event_probability=0.0, dt=1e-6, seed=3)
        rows = [list(sim.step().values()) for _ in range(20000)]
        r = np.diff(np.log(np.array(rows)), axis=0)
        corr = np.corrcoef(r.T)
        assert corr[0, 1] == pytest.approx(0.6, abs=0.06)  # AAPL-MSFT
        assert corr[0, 2] == pytest.approx(0.3, abs=0.06)  # AAPL-JPM

    def test_known_and_unknown_start_prices(self):
        sim = GBMSimulator(["PYPL", "ZZZZ"], seed=5)
        assert sim.get_price("PYPL") == 65.0
        assert 50 <= sim.get_price("ZZZZ") <= 300

    def test_default_ten_tickers_cholesky_ok(self):
        from app.market.seed_prices import SEED_PRICES

        sim = GBMSimulator(list(SEED_PRICES), seed=1)
        assert sim._cholesky is not None and len(sim.step()) == 10

    async def test_source_sets_prev_close_and_normalises(self):
        cache = PriceCache()
        src = SimulatorDataSource(cache, update_interval=0.01, seed=1)
        await src.start(["aapl"])
        await src.add_ticker("pypl ")
        await asyncio.sleep(0.05)
        await src.stop()
        assert cache.get("AAPL").prev_close == 190.0 and cache.get("PYPL").prev_close == 65.0
        assert src.get_tickers() == ["AAPL", "PYPL"] and src.mode == "simulator"


class FakeRequest:
    client = None

    def __init__(self, disconnect_after: int):
        self.n, self.limit = 0, disconnect_after

    async def is_disconnected(self):
        self.n += 1
        return self.n > self.limit


class TestSSE:
    async def test_data_event_then_heartbeat_then_removal(self):
        cache = PriceCache()
        cache.update("AAPL", 190.0, prev_close=189.0)
        gen = _generate_events(cache, FakeRequest(8), interval=0.01, heartbeat=0.03)
        out = [await gen.__anext__() for _ in range(3)]
        assert out[0] == "retry: 1000\n\n"
        payload = json.loads(out[1].removeprefix("data: "))
        assert payload["AAPL"]["prev_close"] == 189.0 and payload["AAPL"]["day_change"] == 1.0
        assert out[2] == ": keepalive\n\n"
        cache.remove("AAPL")  # removal bumps the version -> client receives {}
        rest = [chunk async for chunk in gen]
        assert "data: {}\n\n" in rest

    def test_router_factory_is_repeatable(self):
        from app.market import create_stream_router

        routes = lambda r: [x.path for x in r.routes]  # noqa: E731
        assert routes(create_stream_router(PriceCache())) == ["/api/stream/prices"]
        assert routes(create_stream_router(PriceCache())) == ["/api/stream/prices"]


class TestFactory:
    def test_selection(self, monkeypatch):
        monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
        assert type(create_market_data_source(PriceCache())).__name__ == "SimulatorDataSource"
        monkeypatch.setenv("MASSIVE_API_KEY", "   ")
        assert type(create_market_data_source(PriceCache())).__name__ == "SimulatorDataSource"
        monkeypatch.setenv("MASSIVE_API_KEY", "k")
        assert isinstance(create_market_data_source(PriceCache()), MassiveDataSource)
        monkeypatch.setenv("MARKET_FORCE_SIMULATOR", "true")
        assert type(create_market_data_source(PriceCache())).__name__ == "SimulatorDataSource"

    async def test_bad_key_falls_back_to_degraded_simulator(self, monkeypatch):
        monkeypatch.setenv("MASSIVE_API_KEY", "bad")
        monkeypatch.delenv("MARKET_FORCE_SIMULATOR", raising=False)

        from tests.market.test_massive_source import FakeClient

        monkeypatch.setattr(
            "app.market.massive_client.make_client",
            lambda *a, **k: FakeClient(snapshots=AuthError("Unknown API Key")),
        )
        cache = PriceCache()
        src = await start_market_data(cache, ["AAPL"])
        try:
            assert src.mode == "simulator" and src.status()["degraded"] is True
            assert cache.get_price("AAPL") is not None
        finally:
            await src.stop()

    def test_make_client_accepts_our_kwargs(self):
        client = make_client("k", 5.0)
        assert client.retries == 0
