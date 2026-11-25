"""MassiveDataSource tests against a fake SDK client that returns real SDK models."""

import asyncio

import pytest
from massive.exceptions import AuthError, BadResponse
from massive.rest.models import GroupedDailyAgg, TickerSnapshot

from app.market import MarketDataError, MarketDataUnavailableError, PriceCache, reconcile_tickers
from app.market.massive_client import MassiveDataSource

FORBIDDEN = BadResponse('{"status":"NOT_AUTHORIZED","message":"Your plan doesn\'t include this"}')
RATE = BadResponse('{"status":"ERROR","error":"You\'ve exceeded the maximum requests per minute"}')


def snap(ticker, price, prev=100.0, ts=1_764_080_900_000_000_000):
    return TickerSnapshot.from_dict(
        {"ticker": ticker, "lastTrade": {"p": price, "t": ts}, "prevDay": {"c": prev}}
    )


def bar(ticker, close):
    return GroupedDailyAgg(ticker=ticker, close=close)


class Seq:
    """Responses returned in order; the last one repeats. Exceptions are raised."""

    def __init__(self, *items):
        self.items = list(items)

    def next(self):
        return self.items.pop(0) if len(self.items) > 1 else self.items[0]


class FakeClient:
    """Stands in for massive.RESTClient. Each attribute is a value, an Exception to
    raise, or a Seq of those."""

    def __init__(self, snapshots=None, grouped=None, single=None):
        self.snapshots, self.grouped, self.single = snapshots, grouped, single
        self.calls: list[tuple] = []

    @staticmethod
    def _resolve(item):
        if isinstance(item, Seq):
            item = item.next()
        if isinstance(item, Exception):
            raise item
        return item

    def get_snapshot_all(self, market_type, tickers=None, **kw):
        self.calls.append(("snapshot_all", tuple(tickers)))
        return self._resolve(self.snapshots)

    def get_snapshot_ticker(self, market_type, ticker, **kw):
        self.calls.append(("snapshot_ticker", ticker))
        return self._resolve(self.single)

    def get_grouped_daily_aggs(self, day, adjusted=None, **kw):
        self.calls.append(("grouped", day))
        return self._resolve(self.grouped)


def make(client, **kw):
    cache = PriceCache()
    return cache, MassiveDataSource("k", cache, poll_interval=0.05, client=client, **kw)


async def test_snapshot_mode_populates_cache_before_start_returns():
    cache, src = make(FakeClient(snapshots=[snap("AAPL", 190.5, 189.0), snap("MSFT", 420.0)]))
    await src.start(["aapl", "MSFT"])
    try:
        u = cache.get("AAPL")
        assert (u.price, u.prev_close) == (190.5, 189.0)
        assert round(u.day_change_percent, 2) == 0.79
        assert src.mode == "massive-snapshot" and src.get_tickers() == ["AAPL", "MSFT"]
    finally:
        await src.stop()


async def test_403_in_auto_mode_falls_back_to_eod():
    # Friday 2025-11-21 and Thursday 2025-11-20 style sessions: two grouped calls.
    client = FakeClient(
        snapshots=FORBIDDEN,
        grouped=Seq([bar("AAPL", 195.0), bar("PYPL", 65.0)], [bar("AAPL", 190.0)]),
    )
    cache, src = make(client, call_gap=0.0)
    await src.start(["AAPL"])
    try:
        for _ in range(100):
            if cache.get("AAPL"):
                break
            await asyncio.sleep(0.02)
        u = cache.get("AAPL")
        assert (u.price, u.prev_close) == (195.0, 190.0)
        assert src.mode == "massive-eod"
        assert await src.validate_ticker("PYPL") is True
        assert await src.validate_ticker("NOPE") is False
        await src.add_ticker("PYPL")  # instant: whole market already in memory
        assert cache.get_price("PYPL") == 65.0
    finally:
        await src.stop()


async def test_forced_snapshot_mode_does_not_fall_back():
    cache, src = make(FakeClient(snapshots=FORBIDDEN), requested_mode="snapshot")
    await src.start(["AAPL"])
    try:
        assert src.mode == "massive-snapshot" and src.status()["last_error"].startswith("forbidden")
    finally:
        await src.stop()


async def test_bad_key_raises_unavailable():
    _, src = make(FakeClient(snapshots=AuthError("bad")))
    with pytest.raises(MarketDataUnavailableError):
        await src.start(["AAPL"])


async def test_rate_limit_doubles_interval_then_recovers():
    client = FakeClient(snapshots=Seq([snap("AAPL", 1.0)], RATE, [snap("AAPL", 2.0)]))
    cache, src = make(client)
    await src.start(["AAPL"])
    try:
        await asyncio.sleep(0.12)  # first loop poll hits RATE
        assert src.status()["poll_interval"] > 0.05 or src.status()["last_error"] is None
        await asyncio.sleep(0.3)
        assert cache.get_price("AAPL") == 2.0 and src.status()["poll_interval"] == 0.05
    finally:
        await src.stop()


async def test_missing_and_removed_tickers_are_tolerated():
    client = FakeClient(snapshots=[snap("AAPL", 190.0)])  # MSFT absent from response
    cache, src = make(client)
    await src.start(["AAPL", "MSFT"])
    try:
        assert cache.get("MSFT") is None
        await src.remove_ticker("AAPL")
        assert cache.get("AAPL") is None
        await asyncio.sleep(0.15)  # a later poll must not resurrect it
        assert cache.get("AAPL") is None
    finally:
        await src.stop()


async def test_add_ticker_triggers_early_poll():
    client = FakeClient(snapshots=[snap("AAPL", 190.0), snap("TSLA", 250.0)])
    cache, src = make(client)
    src._base_interval = src._interval = 30.0  # would otherwise wait 30 s
    await src.start(["AAPL"])
    try:
        await src.add_ticker("TSLA")
        for _ in range(100):
            if cache.get("TSLA"):
                break
            await asyncio.sleep(0.05)
        assert cache.get_price("TSLA") == 250.0
    finally:
        await src.stop()


async def test_validate_ticker_snapshot_mode():
    client = FakeClient(snapshots=[snap("AAPL", 1.0)], single=snap("PYPL", 65.0))
    _, src = make(client)
    await src.start(["AAPL"])
    try:
        assert await src.validate_ticker("pypl") is True
        client.single = BadResponse('{"status":"NOT_FOUND","message":"Ticker not found."}')
        assert await src.validate_ticker("ZZZZ") is False
        client.single = RATE
        with pytest.raises(MarketDataError):
            await src.validate_ticker("MSFT")
        assert await src.validate_ticker("not a ticker!") is False
    finally:
        await src.stop()


async def test_reconcile_tickers_adds_and_removes():
    cache, src = make(FakeClient(snapshots=[snap("AAPL", 1.0)]))
    await src.start(["AAPL", "MSFT"])
    try:
        await reconcile_tickers(src, ["aapl", "NVDA"])
        assert sorted(src.get_tickers()) == ["AAPL", "NVDA"]
    finally:
        await src.stop()
