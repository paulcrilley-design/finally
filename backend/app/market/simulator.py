"""GBM-based market simulator."""

from __future__ import annotations

import asyncio
import logging
import math
import random

import numpy as np

from .cache import PriceCache
from .interface import MarketDataSource, is_valid_symbol, normalize_ticker
from .seed_prices import (
    CORRELATION_GROUPS,
    CROSS_GROUP_CORR,
    DEFAULT_PARAMS,
    INTRA_FINANCE_CORR,
    INTRA_TECH_CORR,
    KNOWN_PRICES,
    SEED_PRICES,
    TICKER_PARAMS,
    TSLA_CORR,
    UNKNOWN_PRICE_RANGE,
)

logger = logging.getLogger(__name__)


class GBMSimulator:
    """Geometric Brownian Motion simulator for correlated stock prices.

    S(t+dt) = S(t) * exp((mu - sigma^2/2) * dt + sigma * sqrt(dt) * Z)

    Pure and synchronous: no asyncio, no cache. Pass `seed` for a reproducible
    series (own RNGs, so seeding never touches global random state).
    """

    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600  # 5,896,800
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR  # ~8.48e-8 for a 500 ms tick

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.001,
        seed: int | None = None,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability
        self._np_rng = np.random.default_rng(seed)
        self._rng = random.Random(seed)

        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._open_prices: dict[str, float] = {}  # "previous close" baseline
        self._params: dict[str, dict[str, float]] = {}
        self._cholesky: np.ndarray | None = None

        for ticker in tickers:
            self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    # --- Public API ---

    def step(self) -> dict[str, float]:
        """Advance every ticker one tick. Returns {ticker: price rounded to 2 dp}."""
        n = len(self._tickers)
        if n == 0:
            return {}

        z = self._np_rng.standard_normal(n)
        if self._cholesky is not None:
            z = self._cholesky @ z

        sqrt_dt = math.sqrt(self._dt)
        result: dict[str, float] = {}
        for i, ticker in enumerate(self._tickers):
            mu = self._params[ticker]["mu"]
            sigma = self._params[ticker]["sigma"]
            self._prices[ticker] *= math.exp(
                (mu - 0.5 * sigma**2) * self._dt + sigma * sqrt_dt * z[i]
            )

            if self._rng.random() < self._event_prob:
                magnitude = self._rng.uniform(0.02, 0.05)
                sign = self._rng.choice((-1, 1))
                self._prices[ticker] *= 1 + magnitude * sign
                logger.debug("Event on %s: %+.1f%%", ticker, magnitude * sign * 100)

            result[ticker] = round(self._prices[ticker], 2)
        return result

    def add_ticker(self, ticker: str) -> None:
        if ticker in self._prices:
            return
        self._add_ticker_internal(ticker)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        del self._open_prices[ticker]
        del self._params[ticker]
        self._rebuild_cholesky()

    def get_price(self, ticker: str) -> float | None:
        return self._prices.get(ticker)

    def get_open_price(self, ticker: str) -> float | None:
        """Price when the ticker joined the simulation: our 'previous close'."""
        return self._open_prices.get(ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    # --- Internals ---

    def _starting_price(self, ticker: str) -> float:
        if ticker in SEED_PRICES:
            return SEED_PRICES[ticker]
        if ticker in KNOWN_PRICES:
            return KNOWN_PRICES[ticker]
        return round(self._rng.uniform(*UNKNOWN_PRICE_RANGE), 2)

    def _add_ticker_internal(self, ticker: str) -> None:
        if ticker in self._prices:
            return
        price = self._starting_price(ticker)
        self._tickers.append(ticker)
        self._prices[ticker] = price
        self._open_prices[ticker] = price
        self._params[ticker] = TICKER_PARAMS.get(ticker, dict(DEFAULT_PARAMS))

    def _rebuild_cholesky(self) -> None:
        n = len(self._tickers)
        if n <= 1:
            self._cholesky = None
            return

        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                rho = self._pairwise_correlation(self._tickers[i], self._tickers[j])
                corr[i, j] = rho
                corr[j, i] = rho

        try:
            self._cholesky = np.linalg.cholesky(corr)
        except np.linalg.LinAlgError:  # cannot happen with the constants, but never crash
            logger.warning("Correlation matrix not positive definite; using independent moves")
            self._cholesky = None

    @staticmethod
    def _pairwise_correlation(t1: str, t2: str) -> float:
        tech = CORRELATION_GROUPS["tech"]
        finance = CORRELATION_GROUPS["finance"]
        if t1 == "TSLA" or t2 == "TSLA":
            return TSLA_CORR
        if t1 in tech and t2 in tech:
            return INTRA_TECH_CORR
        if t1 in finance and t2 in finance:
            return INTRA_FINANCE_CORR
        return CROSS_GROUP_CORR


class SimulatorDataSource(MarketDataSource):
    """MarketDataSource backed by GBMSimulator.

    A background asyncio task steps the simulator every `update_interval` seconds
    and writes each price to the PriceCache.
    """

    def __init__(
        self,
        price_cache: PriceCache,
        update_interval: float = 0.5,
        event_probability: float = 0.001,
        seed: int | None = None,
        degraded_reason: str | None = None,
    ) -> None:
        self._cache = price_cache
        self._interval = update_interval
        self._event_prob = event_probability
        self._seed = seed
        self._degraded_reason = degraded_reason  # set when used as a Massive fallback
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    @property
    def mode(self) -> str:
        return "simulator"

    def status(self) -> dict:
        return {
            "mode": self.mode,
            "degraded": self._degraded_reason is not None,
            "degraded_reason": self._degraded_reason,
            "tickers": len(self.get_tickers()),
        }

    async def start(self, tickers: list[str]) -> None:
        names = list(dict.fromkeys(normalize_ticker(t) for t in tickers))
        self._sim = GBMSimulator(names, event_probability=self._event_prob, seed=self._seed)
        for ticker in names:  # seed the cache so SSE and trades have prices at once
            self._write(ticker, self._sim.get_price(ticker))
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")
        logger.info("Simulator started with %d tickers", len(names))

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Simulator stopped")

    async def add_ticker(self, ticker: str) -> None:
        ticker = normalize_ticker(ticker)
        if self._sim and is_valid_symbol(ticker):
            self._sim.add_ticker(ticker)
            self._write(ticker, self._sim.get_price(ticker))
            logger.info("Simulator: added ticker %s", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        ticker = normalize_ticker(ticker)
        if self._sim:
            self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)
        logger.info("Simulator: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return self._sim.get_tickers() if self._sim else []

    def _write(self, ticker: str, price: float | None) -> None:
        if price is None or self._sim is None:
            return
        self._cache.update(ticker, price, prev_close=self._sim.get_open_price(ticker))

    async def _run_loop(self) -> None:
        while True:
            try:
                if self._sim:
                    for ticker, price in self._sim.step().items():
                        self._write(ticker, price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
