"""Tests for the MarketDataSource base class and ticker helpers."""

from app.market.interface import MarketDataSource, clean_tickers


class MinimalSource(MarketDataSource):
    """Implements only the abstract methods, to exercise the base-class defaults."""

    async def start(self, tickers):
        pass

    async def stop(self):
        pass

    async def add_ticker(self, ticker):
        pass

    async def remove_ticker(self, ticker):
        pass

    def get_tickers(self):
        return ["AAPL"]


async def test_default_capabilities():
    source = MinimalSource()
    assert source.mode == "unknown"
    assert source.status() == {"mode": "unknown", "degraded": False, "tickers": 1}
    assert await source.validate_ticker(" brk.b ") is True
    assert await source.validate_ticker("1bad!") is False


def test_clean_tickers_keeps_order_and_drops_invalid():
    assert clean_tickers(["msft", " AAPL ", "MSFT", "", "no good"]) == ["MSFT", "AAPL"]
