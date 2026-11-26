"""Regression tests for the code-review fixes (items 1-11)."""

import asyncio
import logging

import pytest
from massive.exceptions import AuthError, BadResponse

from app.market import PriceCache, reconcile_tickers, start_market_data
from app.market.factory import _env_seed
from app.market.massive_client import MassiveDataSource
from app.market.massive_parse import ErrorKind, classify_error
from app.market.simulator import GBMSimulator, SimulatorDataSource

from .test_massive_source import FakeClient, Seq, bar, make, snap


def test_unknown_ticker_start_price_is_deterministic():
    a = GBMSimulator(["ZZQX"], seed=1).get_price("ZZQX")
    b = GBMSimulator(["ZZQX"], seed=2).get_price("ZZQX")
    assert a == b and 50.0 <= a <= 300.0


@pytest.mark.parametrize(
    "raw,expected",
    [("42", 42), ("0", 0), ("-7", None), ("--5", None), ("x", None), ("", None)],
)
def test_env_seed_never_raises(monkeypatch, raw, expected):
    monkeypatch.setenv("SIM_SEED", raw)
    assert _env_seed() == expected


@pytest.mark.parametrize("raw", ["-7", "0", "x"])
async def test_any_sim_seed_still_starts(monkeypatch, raw):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.setenv("SIM_SEED", raw)
    cache = PriceCache()
    src = await start_market_data(cache, ["AAPL"])
    try:
        assert cache.get_price("AAPL") == 190.0
    finally:
        await src.stop()


def test_classify_error_is_not_fooled_by_substrings():
    assert classify_error(RuntimeError("connect to host:4290 failed")) is ErrorKind.NETWORK
    body = BadResponse('{"error":"see api key docs"}')
    assert classify_error(body) is ErrorKind.OTHER
    assert classify_error(BadResponse('{"error":"Unknown API Key"}')) is ErrorKind.AUTH


async def test_double_start_is_rejected():
    sim = SimulatorDataSource(PriceCache())
    await sim.start(["AAPL"])
    try:
        with pytest.raises(RuntimeError):
            await sim.start(["AAPL"])
    finally:
        await sim.stop()
    await sim.start(["AAPL"])  # restart after stop is fine
    await sim.stop()

    _, src = make(FakeClient(snapshots=[snap("AAPL", 1.0)]))
    await src.start(["AAPL"])
    try:
        with pytest.raises(RuntimeError):
            await src.start(["AAPL"])
    finally:
        await src.stop()


async def test_reconcile_skips_and_warns_once_for_invalid_symbols(caplog):
    sim = SimulatorDataSource(PriceCache())
    await sim.start(["AAPL"])
    try:
        with caplog.at_level(logging.WARNING, logger="app.market.tracking"):
            await reconcile_tickers(sim, ["AAPL", "bad symbol!"])
            await reconcile_tickers(sim, ["AAPL", "bad symbol!"])
        assert sim.get_tickers() == ["AAPL"]
        assert sum("BAD SYMBOL!" in r.message for r in caplog.records) == 1
        assert not any("Tracked tickers" in r.message for r in caplog.records)
    finally:
        await sim.stop()


async def test_eod_publishes_latest_closes_before_second_call_finishes():
    gate = asyncio.Event()

    class SlowClient(FakeClient):
        def get_grouped_daily_aggs(self, day, adjusted=None, **kw):
            self.calls.append(("grouped", day))
            if len([c for c in self.calls if c[0] == "grouped"]) > 1:
                # Second (prior-session) call: block this worker thread until released.
                import time

                while not gate.is_set():
                    time.sleep(0.01)
                return [bar("AAPL", 190.0)]
            return [bar("AAPL", 195.0)]

    cache, src = make(
        SlowClient(snapshots=BadResponse("NOT_AUTHORIZED doesn't include")), call_gap=0.0
    )
    await src.start(["AAPL"])
    try:
        for _ in range(100):
            if cache.get("AAPL"):
                break
            await asyncio.sleep(0.02)
        assert cache.get("AAPL").price == 195.0  # visible while the baseline call is pending
        assert cache.get("AAPL").prev_close is None
        gate.set()
        for _ in range(100):
            if cache.get("AAPL").prev_close:
                break
            await asyncio.sleep(0.02)
        assert cache.get("AAPL").prev_close == 190.0
    finally:
        gate.set()
        await src.stop()


async def test_runtime_auth_failure_falls_back_to_simulator():
    client = FakeClient(snapshots=Seq([snap("AAPL", 190.0)], AuthError("revoked")))
    cache, src = make(client)
    await src.start(["AAPL"])
    try:
        for _ in range(100):
            if src.mode == "simulator":
                break
            await asyncio.sleep(0.02)
        assert src.mode == "simulator"
        assert src.status()["degraded"] is True
        await src.add_ticker("MSFT")
        assert sorted(src.get_tickers()) == ["AAPL", "MSFT"]
        assert cache.get("MSFT") is not None
    finally:
        await src.stop()


async def test_validate_calls_are_spaced():
    client = FakeClient(snapshots=[snap("AAPL", 1.0)], single=snap("PYPL", 65.0))
    _, src = make(client, validate_gap=0.15)
    await src.start(["AAPL"])
    try:
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        await asyncio.gather(*(src.validate_ticker("PYPL") for _ in range(3)))
        assert loop.time() - t0 >= 0.28  # two gaps of 0.15 s
    finally:
        await src.stop()


def test_massive_source_constructor_unchanged():
    assert MassiveDataSource("k", PriceCache()).status()["mode"] == "massive-snapshot"
