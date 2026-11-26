"""Integration tests for SimulatorDataSource."""

import asyncio

import pytest

from app.market.cache import PriceCache
from app.market.simulator import SimulatorDataSource

from .helpers import wait_until


@pytest.mark.asyncio
class TestSimulatorDataSource:
    """Integration tests for the SimulatorDataSource."""

    async def test_start_populates_cache(self):
        """Test that start() immediately populates the cache."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "GOOGL"])

        # Cache should have seed prices immediately (before first loop tick)
        assert cache.get("AAPL") is not None
        assert cache.get("GOOGL") is not None

        await source.stop()

    async def test_prices_update_over_time(self):
        """Test that prices are updated periodically."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.01)
        await source.start(["AAPL"])

        initial_version = cache.version
        # Several update cycles
        await wait_until(lambda: cache.version >= initial_version + 3)

        await source.stop()

    async def test_stop_is_clean(self):
        """Test that stop() is clean and idempotent."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL"])
        await source.stop()
        # Double stop should not raise
        await source.stop()

    async def test_add_ticker(self):
        """Test adding a ticker dynamically."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL"])

        await source.add_ticker("TSLA")
        assert "TSLA" in source.get_tickers()
        assert cache.get("TSLA") is not None

        await source.stop()

    async def test_remove_ticker(self):
        """Test removing a ticker."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "TSLA"])

        await source.remove_ticker("TSLA")
        assert "TSLA" not in source.get_tickers()
        assert cache.get("TSLA") is None

        await source.stop()

    async def test_get_tickers(self):
        """Test getting the list of active tickers."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "GOOGL"])

        tickers = source.get_tickers()
        assert set(tickers) == {"AAPL", "GOOGL"}

        await source.stop()

    async def test_empty_start(self):
        """Test starting with no tickers."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start([])

        assert len(cache) == 0
        assert source.get_tickers() == []

        await source.stop()

    async def test_exception_resilience(self, monkeypatch, caplog):
        """A failing step is logged and the loop carries on."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.01)
        await source.start(["AAPL"])
        real_step = source._sim.step
        calls = 0

        def flaky_step():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("boom")
            return real_step()

        monkeypatch.setattr(source._sim, "step", flaky_step)
        version = cache.version
        try:
            await wait_until(lambda: cache.version > version)
            assert calls >= 2
            assert not source._task.done()
            assert "Simulator step failed" in caplog.text
        finally:
            await source.stop()

    async def test_stop_halts_updates(self):
        """No writes happen after stop()."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.01)
        await source.start(["AAPL"])
        await source.stop()
        version = cache.version

        await asyncio.sleep(0.05)

        assert cache.version == version

    async def test_custom_update_interval(self):
        """The interval controls the cadence: a long one means no tick yet."""
        slow_cache, fast_cache = PriceCache(), PriceCache()
        slow = SimulatorDataSource(price_cache=slow_cache, update_interval=60.0)
        fast = SimulatorDataSource(price_cache=fast_cache, update_interval=0.01)
        await slow.start(["AAPL"])
        await fast.start(["AAPL"])
        try:
            await wait_until(lambda: fast_cache.version >= 5)
            assert slow_cache.version <= 2  # the start() seed plus at most the first tick
        finally:
            await slow.stop()
            await fast.stop()

    async def test_custom_event_probability(self):
        """With event_probability=1.0 every tick is a 2-5% shock."""
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.01, event_probability=1.0)
        await source.start(["AAPL"])
        version = cache.version
        try:
            await wait_until(lambda: cache.version > version)
            assert 1.9 <= abs(cache.get("AAPL").change_percent) <= 5.1
        finally:
            await source.stop()
