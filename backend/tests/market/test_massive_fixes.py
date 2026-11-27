"""Regression tests for the Massive findings in MARKET_DATA_REVIEW.md."""

import asyncio
import socket
import time

import pytest
from massive.exceptions import AuthError

from app.market import MarketDataError, MarketDataUnavailableError, PriceCache
from app.market.factory import create_market_data_source
from app.market.massive_client import MassiveCallError, make_client

from .helpers import wait_until
from .test_massive_source import FORBIDDEN, RATE, FakeClient, Seq, bar, make, snap


async def test_empty_watchlist_still_checks_the_plan():
    client = FakeClient(snapshots=FORBIDDEN, grouped=[bar("AAPL", 195.0)])
    cache, src = make(client, call_gap=0.0)
    await src.start([])
    try:
        assert src.mode == "massive-eod" and cache.get_all() == {}
    finally:
        await src.stop()


async def test_empty_watchlist_still_checks_the_key():
    _, src = make(FakeClient(snapshots=AuthError("bad")))
    with pytest.raises(MarketDataUnavailableError):
        await src.start([])


async def test_validate_ticker_switches_to_eod_on_403():
    client = FakeClient(snapshots=[], single=FORBIDDEN, grouped=[bar("PYPL", 65.0)])
    _, src = make(client, call_gap=0.0)
    src._base_interval = src._interval = 30.0
    await src.start([])
    try:
        with pytest.raises(MarketDataError):
            await src.validate_ticker("PYPL")
        await wait_until(lambda: bool(src._eod_closes))  # woken, not 30 s later
        assert await src.validate_ticker("PYPL") is True
    finally:
        await src.stop()


@pytest.mark.parametrize("via_validate", [False, True])
async def test_fallback_continues_from_the_last_real_prices(via_validate):
    client = FakeClient(
        snapshots=Seq([snap("AAPL", 260.0, 255.0)], AuthError("revoked")),
        single=AuthError("revoked"),
    )
    cache, src = make(client, fallback_seed=1)
    if via_validate:
        src._base_interval = src._interval = 30.0
    await src.start(["AAPL"])
    try:
        if via_validate:
            assert await src.validate_ticker("PYPL") is True
        await wait_until(lambda: src.mode == "simulator")
        u = cache.get("AAPL")
        assert abs(u.price - 260.0) < 20 and u.prev_close == 255.0
        assert src.status()["degraded"] is True
    finally:
        await src.stop()
    assert src._task is None


async def test_make_client_gives_urllib3_a_timeout():
    """A server that accepts and never answers must not hold the thread."""
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        client = make_client("k", 0.5)
        client.BASE = f"http://127.0.0.1:{server.getsockname()[1]}"
        started = time.monotonic()
        with pytest.raises(Exception, match="(?i)timed? ?out"):
            await asyncio.wait_for(
                asyncio.to_thread(client.get_grouped_daily_aggs, "2026-01-05"), 10
            )
        assert time.monotonic() - started < 5


async def test_eod_skips_a_refused_newest_session():
    client = FakeClient(grouped=Seq(FORBIDDEN, [bar("AAPL", 120.0)], [bar("AAPL", 110.0)]))
    cache, src = make(client, requested_mode="eod", call_gap=0.0)
    src._tickers = ["AAPL"]
    src._client = client
    await src._refresh_eod()
    u = cache.get("AAPL")
    assert (u.price, u.prev_close) == (120.0, 110.0)


async def test_eod_reports_403_when_every_session_is_refused():
    client = FakeClient(grouped=FORBIDDEN)
    _, src = make(client, requested_mode="eod", call_gap=0.0)
    with pytest.raises(MassiveCallError):
        await src._refresh_eod()
    assert len(client.calls) > 1


@pytest.mark.parametrize("prior", [[bar("AAPL", 110.0)], RATE])
async def test_eod_rollover_never_publishes_a_stale_baseline(prior):
    client = FakeClient(grouped=Seq([bar("AAPL", 110.0)], [bar("AAPL", 100.0)]))
    cache, src = make(client, requested_mode="eod", call_gap=0.0)
    src._tickers = ["AAPL"]
    await src._refresh_eod()
    src._eod_day = None  # pretend the loaded session is an older one
    seen = []
    update = cache.update

    def record(*args, **kwargs):
        seen.append(update(*args, **kwargs))
        return seen[-1]

    cache.update = record
    client.grouped = Seq([bar("AAPL", 120.0)], prior)
    await src._refresh_eod()
    assert [(u.price, u.prev_close) for u in seen] == [(120.0, 110.0)]


async def test_eod_without_a_baseline_clears_the_old_one():
    client = FakeClient(grouped=Seq([bar("AAPL", 110.0)], [bar("AAPL", 100.0)]))
    cache, src = make(client, requested_mode="eod", call_gap=0.0)
    src._tickers = ["AAPL"]
    await src._refresh_eod()
    client.grouped = Seq([bar("AAPL", 120.0)], [bar("MSFT", 1.0)])
    await src._refresh_eod()
    assert cache.get("AAPL").prev_close is None


async def test_forced_snapshot_mode_stays_forced_in_the_poll_loop():
    client = FakeClient(snapshots=FORBIDDEN)
    _, src = make(client, requested_mode="snapshot")
    await src.start(["AAPL"])
    try:
        await wait_until(lambda: len(client.calls) >= 3)
        assert src.mode == "massive-snapshot"
    finally:
        await src.stop()


async def test_adding_a_ticker_respects_backoff():
    client = FakeClient(snapshots=RATE)
    _, src = make(client)
    src._base_interval = src._interval = 20.0
    await src.start(["AAPL"])
    try:
        for name in ("MSFT", "NVDA", "TSLA"):
            await src.add_ticker(name)
        await asyncio.sleep(1.2)  # longer than the wake-up coalescing pause
        assert len(client.calls) == 1
    finally:
        await src.stop()


@pytest.mark.parametrize("interval", ["nan", "inf"])
def test_bad_massive_settings_use_defaults(monkeypatch, interval):
    monkeypatch.setenv("MASSIVE_API_KEY", "k")
    monkeypatch.setenv("MASSIVE_POLL_INTERVAL", interval)
    monkeypatch.setenv("MASSIVE_MODE", "snapshots")
    monkeypatch.delenv("MARKET_FORCE_SIMULATOR", raising=False)
    src = create_market_data_source(PriceCache())
    assert (src._base_interval, src._requested) == (15.0, "auto")


async def test_restart_leaves_the_fallback_behind():
    client = FakeClient(
        snapshots=Seq([snap("AAPL", 260.0)], AuthError("revoked"), [snap("AAPL", 261.0)])
    )
    cache, src = make(client)
    await src.start(["AAPL"])
    await wait_until(lambda: src.mode == "simulator")
    await src.stop()
    await src.start(["AAPL"])
    try:
        assert src.mode == "massive-snapshot" and cache.get_price("AAPL") == 261.0
    finally:
        await src.stop()
