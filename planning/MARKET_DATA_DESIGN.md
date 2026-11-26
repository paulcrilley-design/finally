# Market Data Backend: Detailed Design

Implementation-ready design for the FinAlly market data subsystem: the unified Python API, the GBM simulator, and the Massive (formerly Polygon.io) client, plus the SSE endpoint and the FastAPI wiring around them.

**Status of this document (2026-11-26).** The design is implemented. The source listings in Sections 3 to 10 are copied from `backend/app/market/`; if they ever differ, the repository wins. The simulator path is ready. **The Massive path has known, unfixed defects and has not been run against the live service: read Section 14.1 before using a Massive key.**

It builds on, and supersedes where they differ, `MASSIVE_API.md` in this folder and the earlier drafts in `archive/` (`MARKET_INTERFACE_V2.md`, `MARKET_SIMULATOR_V2.md`, `MARKET_DATA_DESIGN.md`). Differences are called out in Section 1.2.

---

## Contents

1. [Summary and decisions](#1-summary-and-decisions)
2. [Architecture and files](#2-architecture-and-files)
3. [Data model: `models.py`](#3-data-model-modelspy)
4. [Price cache: `cache.py`](#4-price-cache-cachepy)
5. [Unified interface: `interface.py`](#5-unified-interface-interfacepy)
6. [Simulator: `seed_prices.py`, `simulator.py`](#6-simulator)
7. [Massive API: `massive_parse.py`, `massive_client.py`](#7-massive-api)
8. [Factory and fallback: `factory.py`](#8-factory-and-fallback-factorypy)
9. [SSE endpoint: `stream.py`](#9-sse-endpoint-streampy)
10. [Application wiring: `tracking.py`, `main.py`](#10-application-wiring)
11. [Configuration reference](#11-configuration-reference)
12. [Testing](#12-testing)
13. [Implementation checklist](#13-implementation-checklist)
14. [Open items](#14-open-items)

---

## 1. Summary and decisions

### 1.1 What the subsystem does

One in-memory `PriceCache` holds the latest price for every tracked ticker. Exactly one **producer** writes to it: the GBM simulator by default, or a Massive REST poller when `MASSIVE_API_KEY` is set. Everything else (SSE stream, portfolio valuation, trade execution, watchlist) only **reads** the cache and never knows which producer is running.

```
create_market_data_source(cache)          MASSIVE_API_KEY set (and not forced off)?
        │                                     no                         yes
        │                                      │                          │
        ▼                                      ▼                          ▼
 MarketDataSource (ABC)              SimulatorDataSource        MassiveDataSource
                                      GBM, 500 ms ticks           ├─ "snapshot" mode: 1 call / 15 s, all tickers   (paid plans)
                                                                  └─ "eod" mode: grouped daily bars, hourly         (free plan)
                                              │                           │
                                              └──────────┬────────────────┘
                                                         ▼
                                                    PriceCache (thread-safe, versioned)
                                                         │
                          ┌──────────────┬───────────────┼───────────────┬──────────────┐
                          ▼              ▼               ▼               ▼              ▼
                     SSE stream     Portfolio        Trade exec      Watchlist      /api/health
                                    valuation        (price lookup)  (validate)     (mode, degraded)
```

### 1.2 Changes relative to the code in the repo

The existing implementation (8 modules, 73 tests) is a good base: the interface, cache, factory, simulator math and SSE loop stay. These are the problems found while reading it and checking the installed `massive` SDK, and what this design does about each:

| # | Finding | Evidence | Fix |
|---|---|---|---|
| 1 | **The Massive source never writes a price.** It reads `snap.last_trade.timestamp`, but `LastTrade` has no `timestamp` field (it has `sip_timestamp`, `participant_timestamp`, `trf_timestamp`). The `AttributeError` is caught per ticker and logged as a warning, so the cache stays empty. | `LastTrade.__dataclass_fields__` in the installed SDK. The existing unit tests build `MagicMock` snapshots that *do* have `.timestamp`, which is why they pass. | `extract_quote()` reads real field names; tests build real SDK models with `TickerSnapshot.from_dict(...)`. |
| 2 | **A free key gets no prices.** Snapshots need a paid plan (HTTP 403 `NOT_AUTHORIZED`), and the code assumes snapshots. | `MASSIVE_API.md` section 3. | Mode detection with an end-of-day fallback built on grouped daily bars (Section 7.4). |
| 3 | `last_trade` is absent on Starter plans, and `0` values appear before the open. | `MASSIVE_API.md` section 4.1. | Fallback chain `last_trade -> min -> day -> prev_day`, ignoring non-positive prices. |
| 4 | Timestamps are assumed to be milliseconds; the API mixes ns, us, ms and s. | `MASSIVE_API.md` section 8. | `to_unix_seconds()` normalises by magnitude and range. |
| 5 | The SDK's default `retries=3` includes HTTP 429, so a rate limit surfaces as a slow `MaxRetryError` instead of a clean error. | `RESTClient` source (`status_forcelist=[413, 429, ...]`). | `retries=0`, own backoff. |
| 6 | The SDK stores `connect_timeout`/`read_timeout` but never passes them to urllib3, so a hung connection has no deadline. | `BaseClient._get` calls `client.request(...)` with no `timeout=`. | `asyncio.wait_for` around every call. |
| 7 | The SDK raises `BadResponse(body_text)` for every non-200 and does not expose the status code. | `massive/exceptions.py`. | `classify_error()` maps the documented JSON bodies to `ErrorKind`. |
| 8 | "Daily change %" has no baseline (open question 4 in `PLAN.md` section 13). | `PriceUpdate` only has tick-to-tick change. | `prev_close` on `PriceUpdate`, plus `day_change` and `day_change_percent`. |
| 9 | Adding a ticker on Massive shows no price for up to one poll interval (15 s), and there is no way to validate a symbol. | Existing `add_ticker`. | Early wake-up poll on add, and `validate_ticker()`. |
| 10 | Removing a ticker from the cache does not bump `version`, so SSE clients never learn it is gone. A poll in flight can also write a just-removed ticker back. | `PriceCache.remove`, `_poll_once`. | `remove()` bumps the version; the poller re-checks membership before writing. |
| 11 | A bad key leaves the app running with an empty page. | Review item in `archive/MARKET_DATA_REVIEW.md`. | `start_market_data()` falls back to the simulator and reports `degraded: true` in `/api/health`. |
| 12 | Smaller items: simulator did not normalise tickers; unknown tickers always get a random price; no reproducible runs; `create_stream_router` mutated a module-level router; no SSE keep-alive. | Code review. | `normalize_ticker`, `KNOWN_PRICES`, `SIM_SEED`, router built per call, 15 s heartbeat. |

### 1.3 Decisions that close open questions in `PLAN.md` section 13

| Question | Decision |
|---|---|
| Q2: watchlist removal with an open position | The set of tracked tickers is the **union of every user's watchlist and every open position**. Callers never call `add_ticker`/`remove_ticker` directly; they call `reconcile_tickers(source, wanted)` after any change (Section 10.1). |
| Q3: adding arbitrary tickers | Simulator: any `^[A-Z][A-Z0-9.\-]{0,9}$` symbol is accepted; it starts at a believable price from `KNOWN_PRICES` (about 30 popular names) or, failing that, a price in $50 to $300 derived from the symbol, so it is the same after a restart. Massive: validated against the real market (single-ticker snapshot, or the cached whole-market daily bars in end-of-day mode). |
| Q4: baseline for "daily change %" | `prev_close` carried on every `PriceUpdate`. Massive: `prevDay.c` (snapshot mode) or the prior session's close (end-of-day mode). Simulator: the price when the ticker joined the simulation, so it starts at 0% and drifts. |
| Q1 (price-cache part) | A missing price is `None` and a trade is rejected with HTTP 400. Consumers never invent a price. The one source of non-market prices in Massive mode is the declared simulator fallback (Section 7.4), reported by `/api/health`. |
| Trade/UI behaviour under slow feeds | The SSE rate follows the producer (500 ms simulator, 15 s Massive). The frontend must not assume a tick every 500 ms. |

### 1.4 Non-goals

No WebSocket feed from Massive (REST polling only, per the plan), no price history on the backend (sparklines are built client-side from SSE), no persistence of prices across restarts, no per-user price streams.

---

## 2. Architecture and files

```
backend/
  app/
    main.py                    # FastAPI wiring (Section 10.2; owned by the app, shown for the market parts)
    market/
      __init__.py              # public API re-exports
      models.py                # PriceUpdate                                   CHANGED (prev_close, day_change)
      cache.py                 # PriceCache                                    CHANGED (prev_close, remove bumps version)
      interface.py             # MarketDataSource ABC, errors, ticker helpers  CHANGED (mode, validate_ticker, status)
      seed_prices.py           # seed prices, GBM params, correlations         CHANGED (KNOWN_PRICES)
      simulator.py             # GBMSimulator + SimulatorDataSource            CHANGED (seed, prev_close, normalise)
      massive_parse.py         # pure helpers: timestamps, quote extraction    NEW
      massive_client.py        # MassiveDataSource                             REWRITTEN
      factory.py               # create_market_data_source, start_market_data  CHANGED (env options, fallback)
      stream.py                # SSE router                                    CHANGED (heartbeat, router per call)
      tracking.py              # reconcile_tickers                             NEW
  tests/market/
    test_massive_parse.py      NEW        test_massive_source.py   NEW (replaces test_massive.py)
    test_contract.py           NEW        test_design_extras.py    NEW
```

Dependencies are unchanged: `numpy`, `fastapi`, `massive` (already in `pyproject.toml`), and `zoneinfo` from the standard library. `massive` is a core dependency, imported at module top level.

**Threading model.** The simulator runs on the event loop. The Massive SDK is synchronous, so every call goes through `asyncio.to_thread`. The cache is the one shared structure, which is why it uses a `threading.Lock`, not an `asyncio.Lock`.

---

## 3. Data model: `models.py`

`PriceUpdate` is the only value that leaves the market layer. New: `prev_close` (last field, defaulted, so existing constructors keep working) and two derived properties. `day_change` and `day_change_percent` are `None` when the baseline is unknown, so the UI shows a dash instead of a misleading `0%`.

```python
"""Data models for market data."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class PriceUpdate:
    """Immutable snapshot of a single ticker's price at a point in time."""

    ticker: str
    price: float
    previous_price: float
    timestamp: float = field(default_factory=time.time)  # Unix seconds
    prev_close: float | None = None  # Previous session close; baseline for daily change

    @property
    def change(self) -> float:
        """Absolute change versus the previous update (tick to tick)."""
        return round(self.price - self.previous_price, 4)

    @property
    def change_percent(self) -> float:
        """Percentage change versus the previous update (tick to tick)."""
        if self.previous_price == 0:
            return 0.0
        return round((self.price - self.previous_price) / self.previous_price * 100, 4)

    @property
    def direction(self) -> str:
        """'up', 'down', or 'flat' (versus the previous update)."""
        if self.price > self.previous_price:
            return "up"
        elif self.price < self.previous_price:
            return "down"
        return "flat"

    @property
    def day_change(self) -> float | None:
        """Absolute change versus the previous close, or None if unknown."""
        if not self.prev_close:
            return None
        return round(self.price - self.prev_close, 4)

    @property
    def day_change_percent(self) -> float | None:
        """Percentage change versus the previous close, or None if unknown."""
        if not self.prev_close:
            return None
        return round((self.price - self.prev_close) / self.prev_close * 100, 4)

    def to_dict(self) -> dict:
        """Serialize for JSON / SSE transmission."""
        return {
            "ticker": self.ticker,
            "price": self.price,
            "previous_price": self.previous_price,
            "timestamp": self.timestamp,
            "change": self.change,
            "change_percent": self.change_percent,
            "direction": self.direction,
            "prev_close": self.prev_close,
            "day_change": self.day_change,
            "day_change_percent": self.day_change_percent,
        }
```

Example, after a Massive snapshot poll for AAPL:

```python
>>> u = cache.get("AAPL")
>>> u.price, u.previous_price, u.prev_close
(190.5, 190.42, 189.0)
>>> u.direction, u.change, u.day_change_percent
('up', 0.08, 0.7937)
```

---

## 4. Price cache: `cache.py`

Changes: `update()` accepts `prev_close`, which is **sticky** (omit it and the cached value is kept, so simulator ticks do not need to repeat it). `remove()` bumps `version` so SSE clients see the removal, and `version` is read under the lock for consistency.

```python
"""Thread-safe in-memory price cache."""

from __future__ import annotations

import time
from threading import Lock

from .models import PriceUpdate


class PriceCache:
    """Thread-safe in-memory cache of the latest price for each ticker.

    Writers: SimulatorDataSource or MassiveDataSource (one at a time).
    Readers: SSE streaming endpoint, portfolio valuation, trade execution.
    """

    def __init__(self) -> None:
        self._prices: dict[str, PriceUpdate] = {}
        self._lock = Lock()
        self._version: int = 0  # Monotonically increasing; bumped on every update

    def update(
        self,
        ticker: str,
        price: float,
        timestamp: float | None = None,
        prev_close: float | None = None,
    ) -> PriceUpdate:
        """Record a new price for a ticker. Returns the created PriceUpdate.

        Direction and tick change are computed against the cached price. The first
        update for a ticker has previous_price == price (direction 'flat').
        `prev_close` is sticky: if omitted, the value already cached is kept.
        """
        with self._lock:
            ts = timestamp or time.time()
            prev = self._prices.get(ticker)
            previous_price = prev.price if prev else price
            if prev_close is None and prev is not None:
                prev_close = prev.prev_close

            update = PriceUpdate(
                ticker=ticker,
                price=round(price, 2),
                previous_price=round(previous_price, 2),
                timestamp=ts,
                prev_close=round(prev_close, 2) if prev_close else None,
            )
            self._prices[ticker] = update
            self._version += 1
            return update

    def get(self, ticker: str) -> PriceUpdate | None:
        """Get the latest price for a single ticker, or None if unknown."""
        with self._lock:
            return self._prices.get(ticker)

    def get_all(self) -> dict[str, PriceUpdate]:
        """Snapshot of all current prices. Returns a shallow copy."""
        with self._lock:
            return dict(self._prices)

    def get_price(self, ticker: str) -> float | None:
        """Convenience: get just the price float, or None."""
        update = self.get(ticker)
        return update.price if update else None

    def remove(self, ticker: str) -> None:
        """Remove a ticker from the cache (e.g., when removed from watchlist)."""
        with self._lock:
            if self._prices.pop(ticker, None) is not None:
                self._version += 1  # let SSE clients notice the removal

    @property
    def version(self) -> int:
        """Current version counter. Useful for SSE change detection."""
        with self._lock:
            return self._version

    def __len__(self) -> int:
        with self._lock:
            return len(self._prices)

    def __contains__(self, ticker: str) -> bool:
        with self._lock:
            return ticker in self._prices
```

Consumer rules (unchanged): `get_price()` returning `None` means "no price known"; reject the trade or show a placeholder. Never substitute a default.

---

## 5. Unified interface: `interface.py`

The abstract methods are unchanged. Added, all with safe defaults so a custom subclass (or a test double) still works:

- `mode` (property): `"simulator"`, `"massive-snapshot"` or `"massive-eod"`, shown by `/api/health` and usable for a UI badge ("Simulated", "Live", "End of day").
- `validate_ticker(ticker)`: is this a real, priceable symbol? Raises `MarketDataError` if the source cannot decide right now (network down, rate limited), which routes map to HTTP 503.
- `status()`: small JSON-able dict for health.
- `normalize_ticker()` and `is_valid_symbol()`: the one canonical form (stripped, upper-case) used at every boundary, so `"aapl"` and `"AAPL"` can never become two tickers.
- `MarketDataError` / `MarketDataUnavailableError`: the second is raised by `start()` only when the source can never work with its configuration (rejected API key); the factory turns it into a simulator fallback.

```python
"""Abstract interface for market data sources."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

logger = logging.getLogger(__name__)

_TICKER_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")  # AAPL, BRK.B, RDS-A


class MarketDataError(Exception):
    """A source could not do what was asked (network, rate limit, bad plan)."""


class MarketDataUnavailableError(MarketDataError):
    """Raised by start() when the source can never work with this config (bad key)."""


def normalize_ticker(ticker: str) -> str:
    """Canonical form used everywhere: stripped and upper-case."""
    return ticker.strip().upper()


def is_valid_symbol(ticker: str) -> bool:
    """Syntax check only. Says nothing about whether the symbol trades."""
    return bool(_TICKER_RE.match(ticker))


def clean_tickers(tickers: Iterable[str]) -> list[str]:
    """Normalise and de-duplicate, keeping order. Invalid symbols are dropped with a warning."""
    names: list[str] = []
    for ticker in dict.fromkeys(normalize_ticker(t) for t in tickers):
        if is_valid_symbol(ticker):
            names.append(ticker)
        else:
            logger.warning("Ignoring invalid ticker symbol %r", ticker)
    return names


class MarketDataSource(ABC):
    """Contract for market data providers.

    Implementations push price updates into a shared PriceCache on their own
    schedule. Downstream code never calls the data source for prices; it reads
    from the cache.

    Lifecycle:
        source = create_market_data_source(cache)
        await source.start(["AAPL", "GOOGL", ...])
        await source.add_ticker("TSLA")
        await source.remove_ticker("GOOGL")
        await source.stop()
    """

    @abstractmethod
    async def start(self, tickers: list[str]) -> None:
        """Begin producing price updates. Call exactly once.

        Implementations pass `tickers` through clean_tickers() first.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop background work. Safe to call repeatedly."""

    @abstractmethod
    async def add_ticker(self, ticker: str) -> None:
        """Track a ticker. No-op if already tracked."""

    @abstractmethod
    async def remove_ticker(self, ticker: str) -> None:
        """Stop tracking a ticker and evict it from the cache. No-op if absent."""

    @abstractmethod
    def get_tickers(self) -> list[str]:
        """Currently tracked tickers."""

    # --- Optional capabilities, with safe defaults -------------------------

    @property
    def mode(self) -> str:
        """'simulator', 'massive-snapshot' or 'massive-eod'. Shown in /api/health."""
        return "unknown"

    async def validate_ticker(self, ticker: str) -> bool:
        """True if `ticker` is a real, priceable symbol for this source.

        Default: syntax check only. Raises MarketDataError if the source cannot
        decide right now (network down, rate limited).
        """
        return is_valid_symbol(normalize_ticker(ticker))

    def status(self) -> dict[str, Any]:
        """Small JSON-able dict for the health endpoint."""
        return {"mode": self.mode, "degraded": False, "tickers": len(self.get_tickers())}
```

(The earlier draft of this design also proposed `get_prev_closes()`. It is dropped: `prev_close` travels on every cached `PriceUpdate`, so nothing needs to ask the source separately.)

---

## 6. Simulator

### 6.1 Approach (recap)

Each ticker follows geometric Brownian motion, `S' = S * exp((mu - sigma^2/2) dt + sigma sqrt(dt) Z)`, with `dt = 0.5 s / 5,896,800 s` (a trading year). Draws are correlated through the Cholesky factor of a sector correlation matrix (tech 0.6, finance 0.5, everything else 0.3), and each tick each ticker has a 0.1% chance of a 2 to 5% shock. The existing math is correct and kept as is. `archive/MARKET_SIMULATOR_V2.md` has the derivation. What changes:

- **Reproducible runs.** `GBMSimulator(seed=...)` owns its RNGs (`numpy.random.Generator` and `random.Random`), so seeding never touches global state. `SIM_SEED=42` in the environment gives identical E2E runs.
- **Believable new tickers.** `KNOWN_PRICES` covers about 30 popular symbols; anything else starts at a price in $50 to $300 derived from a hash of the symbol, with default parameters.
- **Day baseline.** The price when a ticker joins the simulation is its `prev_close`, so the watchlist's daily change starts at 0%.
- **Safety.** A `LinAlgError` from the Cholesky step degrades to independent moves instead of crashing; tickers are normalised and validated at the boundary (`clean_tickers` in `start()`); a fallback instance can carry a `degraded_reason` for `/api/health`.

### 6.2 `seed_prices.py` (append to the existing file)

The existing `SEED_PRICES`, `TICKER_PARAMS`, `DEFAULT_PARAMS`, `CORRELATION_GROUPS` and correlation constants stay exactly as they are. Add:

```python
# Approximate prices for other popular tickers, so a user adding PYPL or AMD gets a
# believable start instead of a random one. Tickers not listed here start at a random
# price in UNKNOWN_PRICE_RANGE. Volatility and drift fall back to DEFAULT_PARAMS.
KNOWN_PRICES: dict[str, float] = {
    "AMD": 160.00, "INTC": 30.00, "ORCL": 170.00, "CRM": 300.00, "ADBE": 520.00,
    "PYPL": 65.00, "SQ": 70.00, "SHOP": 80.00, "UBER": 75.00, "ABNB": 140.00,
    "DIS": 110.00, "NKE": 95.00, "KO": 62.00, "PEP": 170.00, "MCD": 290.00,
    "WMT": 170.00, "COST": 800.00, "HD": 380.00, "BA": 190.00, "CAT": 340.00,
    "GS": 450.00, "MS": 100.00, "BAC": 38.00, "WFC": 58.00, "MA": 470.00,
    "JNJ": 155.00, "PFE": 28.00, "UNH": 520.00, "XOM": 115.00, "CVX": 155.00,
}  # fmt: skip
UNKNOWN_PRICE_RANGE: tuple[float, float] = (50.0, 300.0)
```

### 6.3 `simulator.py`

```python
"""GBM-based market simulator."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import random

import numpy as np

from .cache import PriceCache
from .interface import MarketDataSource, clean_tickers, is_valid_symbol, normalize_ticker
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
        # Deterministic per symbol (not RNG-based) so the price is the same after a
        # restart or re-add; persisted positions keep a meaningful cost basis.
        digest = hashlib.sha256(ticker.encode()).digest()
        frac = int.from_bytes(digest[:8], "big") / 2**64
        low, high = UNKNOWN_PRICE_RANGE
        return round(low + frac * (high - low), 2)

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
        if self._task is not None and not self._task.done():
            raise RuntimeError("SimulatorDataSource already started")
        names = clean_tickers(tickers)
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
```

### 6.4 Examples

```python
sim = GBMSimulator(["AAPL", "MSFT", "JPM"], seed=42)
sim.step()                       # {'AAPL': 190.0, 'MSFT': 420.0, 'JPM': 195.0}  (sub-cent moves round away at 2 dp)
for _ in range(7200): sim.step() # one simulated hour
sim.add_ticker("PYPL")           # starts at 65.00 (KNOWN_PRICES); Cholesky rebuilt
sim.get_open_price("PYPL")       # 65.0  -> prev_close for the watchlist's daily change
```

```python
cache = PriceCache()
src = SimulatorDataSource(cache, update_interval=0.5, seed=42)
await src.start(["aapl", "MSFT"])      # normalised; cache already holds both prices when this returns
await src.add_ticker(" pypl ")         # cache has PYPL immediately, no 500 ms gap
cache.get("PYPL").prev_close           # 65.0
await src.stop()
```

Tuning (`dt`, `update_interval`, `event_probability`, `sigma`/`mu`) is in Section 11. For a livelier demo, raise `dt` (for example x10) rather than sigma, so annualised parameters stay meaningful.

---

## 7. Massive API

### 7.1 What the plan allows

Which plan the key belongs to decides which endpoints work (details and sources in `MASSIVE_API.md` section 3):

| Plan | Snapshots (`/v2/snapshot`) | Grouped daily bars | Rate limit | Our mode |
|---|---|---|---|---|
| Free (Basic) | **403 NOT_AUTHORIZED** | yes, previous sessions only | 5 requests/min | `eod` |
| Starter / Developer | yes, 15-minute delayed; `lastTrade` may be absent | yes | unlimited | `snapshot` |
| Advanced / Business | yes, real-time | yes | unlimited | `snapshot`, poll every 2 to 5 s |

### 7.2 Verified SDK facts (installed `massive` package)

These were checked against the installed SDK source and drive the code. Items still needing a live key are in Section 14.

- `RESTClient(api_key, connect_timeout=10.0, read_timeout=10.0, num_pools=10, retries=3, base="https://api.massive.com", pagination=True, ...)`. Raises `AuthError` only when `api_key is None`.
- `get_snapshot_all(market_type, tickers=None, include_otc=False)` returns `list[TickerSnapshot]`. `get_snapshot_ticker(market_type, ticker)` returns one `TickerSnapshot`. `get_grouped_daily_aggs(date, adjusted=None, locale="us", market_type="stocks", include_otc=False)` returns `list[GroupedDailyAgg]`.
- `TickerSnapshot` fields: `day`, `last_quote`, `last_trade`, `min`, `prev_day`, `ticker`, `todays_change`, `todays_change_percent`, `updated`, `fair_market_value`. `day` and `prev_day` are `Agg` (`open high low close volume vwap timestamp ...`); `min` is `MinuteSnapshot` (`close`, `timestamp`, ...); `last_trade` is `LastTrade` (`price`, `size`, `sip_timestamp`, `participant_timestamp`, `trf_timestamp`, ...).
- `GroupedDailyAgg` fields: `ticker open high low close volume vwap timestamp transactions otc`.
- Every non-200 raises `BadResponse(response_body_text)`. The status code is not available, so errors are classified from the body.
- Snapshot methods need the market type as a string (`SnapshotMarketType.STOCKS.value`). Passing the enum member builds a wrong URL; a test pins the real request URLs.
- Timeouts are stored but not applied; retries include 429 (see Section 1.2, items 5 and 6).

### 7.3 `massive_parse.py`: pure helpers

No I/O and no asyncio, so everything here is unit-tested directly against real SDK models.

- `to_unix_seconds(ts)`: nanoseconds, microseconds, milliseconds or seconds in; Unix seconds out; falls back to "now" for missing, non-numeric, or implausible values (outside the last 10 years to tomorrow).
- `extract_quote(snap)`: best price by preference `last_trade.price` > `min.close` > `day.close` > `prev_day.close`, skipping zeros (`0` means "no data", seen before the open). Also returns `prev_close = prev_day.close`.
- `classify_error(exc)` returns an `ErrorKind`: `AUTH`, `FORBIDDEN`, `RATE_LIMIT`, `NOT_FOUND`, `NETWORK` or `OTHER`.

```python
"""Pure helpers for the Massive client: no I/O, no asyncio, easy to unit test."""

from __future__ import annotations

import enum
import math
import time
from dataclasses import dataclass
from typing import Any

from massive.exceptions import AuthError, BadResponse


def to_unix_seconds(ts: Any, now: float | None = None) -> float:
    """Normalise a Massive timestamp (ns, us, ms or s) to Unix seconds.

    Falls back to `now` (default: time.time()) when the value is missing, not a
    number, or lands outside [now - 10 years, now + 1 day].
    """
    now = time.time() if now is None else now
    if isinstance(ts, bool) or not isinstance(ts, (int, float)) or not math.isfinite(ts) or ts <= 0:
        return now
    if ts > 1e17:
        seconds = ts / 1e9  # nanoseconds
    elif ts > 1e14:
        seconds = ts / 1e6  # microseconds
    elif ts > 1e11:
        seconds = ts / 1e3  # milliseconds
    else:
        seconds = float(ts)
    return seconds if now - 10 * 365 * 86400 <= seconds <= now + 86400 else now


def _positive(x: Any) -> float | None:
    """x as a float if it is a finite number > 0, else None (0 means 'no data')."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return None
    return float(x) if math.isfinite(x) and x > 0 else None


@dataclass(frozen=True, slots=True)
class Quote:
    price: float
    timestamp: float  # Unix seconds
    prev_close: float | None


def extract_quote(snap: Any, now: float | None = None) -> Quote | None:
    """Best available price from one TickerSnapshot, or None if it has no usable price.

    Preference: last_trade (Developer+) > latest minute bar > today's bar > prev day.
    Attribute names are those of massive.rest.models.TickerSnapshot (verified).
    """
    last_trade = getattr(snap, "last_trade", None)
    minute = getattr(snap, "min", None)
    day = getattr(snap, "day", None)
    prev_day = getattr(snap, "prev_day", None)
    prev_close = _positive(getattr(prev_day, "close", None))

    candidates = (
        (
            getattr(last_trade, "price", None),
            getattr(last_trade, "sip_timestamp", None)
            or getattr(last_trade, "participant_timestamp", None)
            or getattr(snap, "updated", None),
        ),
        (getattr(minute, "close", None), getattr(minute, "timestamp", None)),
        (getattr(day, "close", None), getattr(snap, "updated", None)),
    )
    for raw_price, raw_ts in candidates:
        price = _positive(raw_price)
        if price is not None:
            return Quote(price, to_unix_seconds(raw_ts, now), prev_close)
    if prev_close is not None:  # market not open yet: show the last close, flat
        return Quote(prev_close, to_unix_seconds(getattr(snap, "updated", None), now), prev_close)
    return None


class ErrorKind(enum.Enum):
    AUTH = "auth"  # missing / invalid key
    FORBIDDEN = "forbidden"  # plan does not include this endpoint or timeframe
    RATE_LIMIT = "rate_limit"
    NOT_FOUND = "not_found"
    NETWORK = "network"  # DNS, timeout, connection reset, 5xx
    OTHER = "other"


def classify_error(exc: BaseException) -> ErrorKind:
    """Map whatever the client raised to an ErrorKind.

    massive.rest raises BadResponse(<response body text>) for any non-200 and does
    not expose the HTTP status, so we classify on the documented JSON bodies.
    With retries=0 a 429 arrives as BadResponse; with retries>0 urllib3 would raise
    MaxRetryError('... too many 429 error responses'), handled below as well.
    """
    if isinstance(exc, AuthError):
        return ErrorKind.AUTH
    text = str(exc)
    low = text.lower()
    if isinstance(exc, BadResponse):
        if "not_authorized" in low or "doesn't include" in low or "not entitled" in low:
            return ErrorKind.FORBIDDEN
        if "maximum requests" in low or "rate limit" in low or "too many requests" in low:
            return ErrorKind.RATE_LIMIT
        if any(s in low for s in ("unknown api key", "invalid api key", "missing api key")):
            return ErrorKind.AUTH
        if "not_found" in low or "not found" in low:
            return ErrorKind.NOT_FOUND
        return ErrorKind.OTHER
    if "too many 429" in low or "429 error" in low:  # urllib3 MaxRetryError wording
        return ErrorKind.RATE_LIMIT
    return ErrorKind.NETWORK
```

Response bodies the classifier relies on (from `MASSIVE_API.md` section 3; the 401 text is **[unverified]**):

| HTTP | Body (abridged) | `ErrorKind` |
|---|---|---|
| 401 | `{"status":"ERROR","message":"Unknown API Key"}` | `AUTH` |
| 403 | `{"status":"NOT_AUTHORIZED","message":"Your plan doesn't include ..."}` | `FORBIDDEN` |
| 429 | `{"status":"ERROR","error":"You've exceeded the maximum requests per minute ..."}` | `RATE_LIMIT` |
| 404 | `{"status":"NOT_FOUND",...}` | `NOT_FOUND` |
| timeout, DNS, reset | (no body) | `NETWORK` |

### 7.4 `massive_client.py`

Behaviour in one table:

| Situation | Result |
|---|---|
| `start()`, snapshot probe succeeds | `mode = massive-snapshot`; cache is already populated when `start()` returns; loop polls every `poll_interval` (default 15 s) |
| `start()`, probe gets 403, `MASSIVE_MODE=auto` | switch to `massive-eod`; background task loads the last two sessions of whole-market daily bars; warning logged |
| `start()`, probe gets 401 | raises `MarketDataUnavailableError`; `start_market_data()` falls back to the simulator (`degraded: true`) |
| `start()`, probe fails with network / 429 | stay in snapshot mode, keep retrying with backoff (the app is up, prices follow when the network does) |
| 429 while running | interval doubles (cap 120 s), resets to base after the next success |
| 403 while running (plan downgraded) | switch to end-of-day mode |
| 401 while running | polling stops and a simulator takes over the same cache so prices keep moving; `mode` becomes `simulator`, `degraded: true` (decided 2026-11-26) |
| `add_ticker` (snapshot) | wakes the loop for an early poll, so the price appears in about 1 s, not up to 15 s |
| `add_ticker` (eod) | instant: the whole market's closes are already in memory |
| `remove_ticker` | evicts from the cache; an in-flight poll cannot resurrect it |
| ticker missing from a response | cache entry left as is (stale beats empty) |

End-of-day mode details. The free plan allows 5 requests a minute and no same-day data, so: look back from yesterday (US/Eastern), skip weekends without a call, call grouped daily bars for each remaining day until **two** sessions have data (latest close and previous close), keep the **whole market** in memory (about 10,000 entries, a few hundred KB), at least 12.5 s between calls, refresh hourly. A normal weekday costs 2 calls, a weekend or holiday 3 to 4. Prices are stamped with that session's 16:00 Eastern close so a UI can show "as of". They do not move intraday, and the UI should say so (`/api/health` mode `massive-eod`).

```python
"""Massive (formerly Polygon.io) market data source."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime, timedelta
from datetime import time as dtime
from typing import Any
from zoneinfo import ZoneInfo

from massive import RESTClient
from massive.rest.models import SnapshotMarketType

from .cache import PriceCache
from .interface import (
    MarketDataError,
    MarketDataSource,
    MarketDataUnavailableError,
    clean_tickers,
    is_valid_symbol,
    normalize_ticker,
)
from .massive_parse import ErrorKind, classify_error, extract_quote
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)

NEW_YORK = ZoneInfo("America/New_York")
MAX_BACKOFF = 120.0  # seconds
FREE_TIER_CALL_GAP = 12.5  # 5 requests/minute => at most one call per 12 s


class MassiveCallError(Exception):
    """A Massive call failed; `kind` says how, `__cause__` has the original."""

    def __init__(self, kind: ErrorKind, message: str) -> None:
        super().__init__(message)
        self.kind = kind


def make_client(api_key: str, timeout: float) -> RESTClient:
    """RESTClient tuned for polling.

    retries=0: the SDK's default of 3 retries includes HTTP 429, which hides the rate
    limit behind a MaxRetryError and stalls a worker thread. We do our own backoff.
    """
    return RESTClient(api_key=api_key, retries=0, connect_timeout=timeout, read_timeout=timeout)


class MassiveDataSource(MarketDataSource):
    """Polls Massive REST endpoints and writes to the PriceCache.

    mode "snapshot": one /v2/snapshot call per poll for all tickers (paid plans).
    mode "eod":      grouped daily bars, refreshed hourly (free plan; prices are static).
    `requested_mode` "auto" starts in snapshot and drops to eod on a 403.
    """

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
        requested_mode: str = "auto",  # auto | snapshot | eod
        request_timeout: float = 10.0,
        eod_refresh: float = 3600.0,
        call_gap: float | None = None,  # min seconds between eod calls; None = FREE_TIER_CALL_GAP
        client: Any = None,  # injectable for tests
        validate_gap: float = 0.5,  # min seconds between snapshot-mode validate calls
    ) -> None:
        if requested_mode not in ("auto", "snapshot", "eod"):
            raise ValueError(f"bad MASSIVE_MODE: {requested_mode!r}")
        self._api_key = api_key
        self._cache = price_cache
        self._base_interval = poll_interval
        self._interval = poll_interval  # current, grows under rate limiting
        self._requested = requested_mode
        self._timeout = request_timeout
        self._eod_refresh = eod_refresh
        self._call_gap = FREE_TIER_CALL_GAP if call_gap is None else call_gap
        self._client = client
        self._mode = "eod" if requested_mode == "eod" else "snapshot"
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._wakeup = asyncio.Event()
        self._last_call = 0.0
        self._eod_closes: dict[str, float] = {}  # whole market, latest session
        self._eod_prev: dict[str, float] = {}  # whole market, session before
        self._eod_ts: float = 0.0
        self._last_success: float | None = None
        self._last_error: str | None = None
        self._degraded: str | None = None
        self._eod_day: date | None = None  # session last logged, to warn once per session
        self._validate_gap = validate_gap
        self._validate_lock = asyncio.Lock()  # serialises validate calls
        self._last_validate = 0.0
        # Set when the key is rejected at runtime: a simulator takes over so prices keep moving.
        self._fallback: SimulatorDataSource | None = None

    # --- MarketDataSource ---

    @property
    def mode(self) -> str:
        if self._fallback:
            return self._fallback.mode
        return f"massive-{self._mode}"

    def status(self) -> dict[str, Any]:
        if self._fallback:
            return self._fallback.status()
        return {
            "mode": self.mode,
            "degraded": self._degraded is not None,
            "degraded_reason": self._degraded,
            "tickers": len(self._tickers),
            "poll_interval": self._interval,
            "last_success": self._last_success,
            "last_error": self._last_error,
        }

    async def start(self, tickers: list[str]) -> None:
        if self._task is not None and not self._task.done():
            raise RuntimeError("MassiveDataSource already started")
        self._tickers = clean_tickers(tickers)
        self._client = self._client or make_client(self._api_key, self._timeout)

        first_delay = 0.0
        if self._mode == "snapshot":
            try:  # probe: success also fills the cache before start() returns
                await self._poll_snapshot()
                self._on_success()
                first_delay = self._interval
            except MassiveCallError as err:
                if err.kind is ErrorKind.AUTH:
                    raise MarketDataUnavailableError(
                        f"Massive rejected the API key: {err}"
                    ) from err
                if err.kind is ErrorKind.FORBIDDEN and self._requested == "auto":
                    self._switch_to_eod(err)
                else:
                    self._on_error(err)  # network/rate limit: keep trying in the loop
                    first_delay = self._interval
        self._task = asyncio.create_task(self._run(first_delay), name="massive-poller")
        logger.info("Massive source started: mode=%s tickers=%d", self.mode, len(self._tickers))

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        if self._fallback:
            await self._fallback.stop()
        logger.info("Massive source stopped")

    async def add_ticker(self, ticker: str) -> None:
        if self._fallback:
            return await self._fallback.add_ticker(ticker)
        ticker = normalize_ticker(ticker)
        if not is_valid_symbol(ticker) or ticker in self._tickers:
            return
        self._tickers.append(ticker)
        if self._mode == "eod":
            self._apply_eod([ticker])  # whole-market data is already in memory
        else:
            self._wakeup.set()  # poll now instead of waiting up to a full interval

    async def remove_ticker(self, ticker: str) -> None:
        if self._fallback:
            return await self._fallback.remove_ticker(ticker)
        ticker = normalize_ticker(ticker)
        if ticker in self._tickers:
            self._tickers.remove(ticker)
        self._cache.remove(ticker)

    def get_tickers(self) -> list[str]:
        if self._fallback:
            return self._fallback.get_tickers()
        return list(self._tickers)

    async def validate_ticker(self, ticker: str) -> bool:
        if self._fallback:
            return await self._fallback.validate_ticker(ticker)
        ticker = normalize_ticker(ticker)
        if not is_valid_symbol(ticker):
            return False
        if self._mode == "eod":
            if not self._eod_closes:
                raise MarketDataError("End-of-day data is still loading; try again shortly")
            return ticker in self._eod_closes
        async with self._validate_lock:  # one call at a time, spaced out, so adds cannot burst
            wait = self._last_validate + self._validate_gap - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_validate = time.monotonic()
            try:
                snap = await self._call(
                    self._client.get_snapshot_ticker, SnapshotMarketType.STOCKS.value, ticker
                )
            except MassiveCallError as err:
                if err.kind is ErrorKind.NOT_FOUND:
                    return False
                raise MarketDataError(f"Could not validate {ticker}: {err}") from err
        return bool(snap) and getattr(snap, "ticker", None) == ticker

    # --- Background loop ---

    async def _run(self, first_delay: float) -> None:
        delay = first_delay
        while True:
            await self._sleep(delay)
            try:
                if self._mode == "snapshot":
                    await self._poll_snapshot()
                    delay = self._interval
                else:
                    await self._refresh_eod()
                    delay = self._eod_refresh
                self._on_success()
            except MassiveCallError as err:
                if err.kind is ErrorKind.AUTH:
                    await self._fall_back(f"api key rejected: {err}")
                    return  # nothing will work until the key is fixed
                if err.kind is ErrorKind.FORBIDDEN and self._mode == "snapshot":
                    self._switch_to_eod(err)
                    delay = 0.0
                    continue
                self._on_error(err)
                delay = self._interval if self._mode == "snapshot" else min(self._eod_refresh, 300)
            except Exception:  # never let the loop die
                logger.exception("Massive loop error")
                delay = self._interval

    async def _sleep(self, seconds: float) -> None:
        """Sleep, but wake early when a ticker is added; then pause 1 s to coalesce adds."""
        if seconds <= 0:
            return
        try:
            await asyncio.wait_for(self._wakeup.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return
        self._wakeup.clear()
        await asyncio.sleep(1.0)

    # --- Snapshot mode ---

    async def _poll_snapshot(self) -> int:
        tickers = list(self._tickers)
        if not tickers:
            return 0
        snaps = await self._call(
            self._client.get_snapshot_all, SnapshotMarketType.STOCKS.value, tickers
        )
        written = 0
        for snap in snaps:
            ticker = (getattr(snap, "ticker", None) or "").upper()
            if ticker not in self._tickers:  # removed while the call was in flight
                continue
            quote = extract_quote(snap)
            if quote is None:
                logger.debug("Massive: no usable price for %s", ticker)
                continue
            self._cache.update(ticker, quote.price, quote.timestamp, prev_close=quote.prev_close)
            written += 1
        logger.debug("Massive poll: %d/%d tickers updated", written, len(tickers))
        return written

    # --- End-of-day mode ---

    async def _refresh_eod(self) -> None:
        """Load the last two trading sessions (whole market) and publish tracked tickers."""
        last_day: date | None = None
        prev: dict[str, float] | None = None
        day = datetime.now(NEW_YORK).date()
        for _ in range(10):  # weekends are skipped for free; holidays cost one call each
            day -= timedelta(days=1)
            if day.weekday() >= 5:
                continue
            try:
                bars = await self._call(self._client.get_grouped_daily_aggs, day.isoformat(), True)
            except MassiveCallError:
                if last_day is None:
                    raise
                logger.warning("Massive: could not load the prior session; no daily baseline")
                break
            closes = {b.ticker: b.close for b in bars if b.ticker and b.close}
            if not closes:
                continue
            if last_day is None:
                # Publish the latest closes at once; the slow (rate-limited) second call
                # below only adds the previous-close baseline.
                last_day, self._eod_closes = day, closes
                self._eod_ts = datetime.combine(day, dtime(16, 0), tzinfo=NEW_YORK).timestamp()
                self._apply_eod(self._tickers)
            else:
                prev = closes
                break
        if last_day is None:
            raise MassiveCallError(ErrorKind.OTHER, "no grouped daily bars in the last 10 days")

        self._eod_prev = prev or {}
        self._apply_eod(self._tickers)
        level = logging.WARNING if last_day != self._eod_day else logging.DEBUG  # once per session
        self._eod_day = last_day
        logger.log(
            level,
            "Massive end-of-day mode: prices are closes for %s and will not move intraday",
            last_day,
        )

    def _apply_eod(self, tickers: list[str]) -> None:
        for ticker in tickers:
            close = self._eod_closes.get(ticker)
            if close:
                self._cache.update(
                    ticker, close, self._eod_ts, prev_close=self._eod_prev.get(ticker)
                )

    # --- Calling the SDK, backoff, mode switching ---

    async def _call(self, fn: Any, *args: Any) -> Any:
        """Run a blocking SDK call in a thread with a hard deadline; classify failures.

        The SDK stores timeouts but does not pass them to urllib3, so wait_for is the
        real deadline. (A stuck thread is abandoned, not killed; keep calls few.)
        """
        if self._mode == "eod" and self._call_gap:
            wait = self._last_call + self._call_gap - time.monotonic()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()
        try:
            return await asyncio.wait_for(asyncio.to_thread(fn, *args), self._timeout + 5)
        except MassiveCallError:
            raise
        except Exception as exc:  # includes asyncio.TimeoutError
            raise MassiveCallError(classify_error(exc), _safe(exc)) from exc

    def _on_success(self) -> None:
        self._interval = self._base_interval
        self._last_success = time.time()
        self._last_error = None
        self._degraded = None

    def _on_error(self, err: MassiveCallError) -> None:
        self._last_error = f"{err.kind.value}: {err}"
        if err.kind is ErrorKind.RATE_LIMIT:
            self._interval = min(self._interval * 2, MAX_BACKOFF)
            logger.warning("Massive rate limited; polling every %.0fs", self._interval)
        else:
            logger.warning("Massive call failed (%s): %s", err.kind.value, err)

    async def _fall_back(self, reason: str) -> None:
        """The key stopped working: hand over to a simulator so prices keep moving."""
        self._degraded = reason
        self._last_error = reason
        logger.error("Massive source degraded (%s); falling back to the simulator", reason)
        tickers = list(self._tickers)
        self._fallback = SimulatorDataSource(self._cache, degraded_reason=reason)
        await self._fallback.start(tickers)

    def _switch_to_eod(self, err: MassiveCallError) -> None:
        logger.warning("Massive plan has no snapshot access (%s); using end-of-day data", err)
        self._mode = "eod"
        self._degraded = None


def _safe(exc: BaseException) -> str:
    """Error text that can be logged: first 200 chars, API key never included."""
    text = str(exc) or type(exc).__name__
    return text[:200]
```

Example: free key, Wednesday morning, tracking AAPL and MSFT:

```text
INFO   Massive source started: mode=massive-snapshot tickers=2
WARN   Massive plan has no snapshot access ({"status":"NOT_AUTHORIZED",...}); using end-of-day data
         (12 s later, second grouped call)
WARN   Massive end-of-day mode: prices are closes for 2026-11-24 and will not move intraday
```

```json
GET /api/health
{"status": "ok",
 "market": {"mode": "massive-eod", "degraded": false, "degraded_reason": null, "tickers": 2,
            "poll_interval": 15.0, "last_success": 1795597216.7, "last_error": null},
 "prices": 2}
```

Per-call cost of the snapshot mode is one request regardless of ticker count. A paid key polling every 15 s makes 4 requests a minute; Advanced can safely use `MASSIVE_POLL_INTERVAL=2`.

---

## 8. Factory and fallback: `factory.py`

`create_market_data_source(cache)` stays synchronous and returns an unstarted source. New is `start_market_data(cache, tickers)`, which the app lifespan should call: it starts the source, and if Massive reports `MarketDataUnavailableError` (bad key) it logs at ERROR and starts a simulator flagged `degraded` instead. The app stays usable and `/api/health` says why. (The alternative, failing fast at startup, is worse for a demo product.)

```python
"""Factory for creating market data sources."""

from __future__ import annotations

import logging
import os

from .cache import PriceCache
from .interface import MarketDataSource, MarketDataUnavailableError
from .massive_client import MassiveDataSource
from .simulator import SimulatorDataSource

logger = logging.getLogger(__name__)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        logger.warning("Ignoring non-numeric %s=%r", name, raw)
        return default


def _env_seed() -> int | None:
    raw = os.environ.get("SIM_SEED", "").strip()
    if not raw:
        return None
    try:
        seed = int(raw)
    except ValueError:
        seed = -1
    if seed < 0:  # numpy rejects negative seeds
        logger.warning("Ignoring SIM_SEED=%r (must be a non-negative integer)", raw)
        return None
    return seed


def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    """Build (but do not start) the source selected by the environment.

    MASSIVE_API_KEY set and non-empty, and MARKET_FORCE_SIMULATOR not true
        -> MassiveDataSource    (MASSIVE_MODE=auto|snapshot|eod, MASSIVE_POLL_INTERVAL=15)
    otherwise
        -> SimulatorDataSource  (SIM_SEED=<int >= 0> for a reproducible series)
    """
    api_key = os.environ.get("MASSIVE_API_KEY", "").strip()
    force_sim = os.environ.get("MARKET_FORCE_SIMULATOR", "").strip().lower() in ("1", "true", "yes")

    if api_key and not force_sim:
        logger.info("Market data source: Massive API")
        return MassiveDataSource(
            api_key=api_key,
            price_cache=price_cache,
            poll_interval=max(_env_float("MASSIVE_POLL_INTERVAL", 15.0), 1.0),
            requested_mode=os.environ.get("MASSIVE_MODE", "auto").strip().lower() or "auto",
        )
    logger.info("Market data source: GBM simulator")
    return SimulatorDataSource(price_cache=price_cache, seed=_env_seed())


async def start_market_data(price_cache: PriceCache, tickers: list[str]) -> MarketDataSource:
    """Create and start a source. If Massive cannot work (bad key), fall back to the
    simulator so the app stays usable; /api/health then reports degraded=true."""
    source = create_market_data_source(price_cache)
    try:
        await source.start(tickers)
        return source
    except MarketDataUnavailableError as err:
        logger.error("Massive unavailable (%s); falling back to the simulator", err)
        await source.stop()
        fallback = SimulatorDataSource(
            price_cache=price_cache, seed=_env_seed(), degraded_reason=str(err)
        )
        await fallback.start(tickers)
        return fallback
```

---

## 9. SSE endpoint: `stream.py`

`GET /api/stream/prices`, unchanged contract: `retry: 1000`, then one `data:` event holding **all** tracked tickers whenever `cache.version` changed. Changes: a `: keepalive` comment every 15 s while nothing changes (end-of-day mode can be quiet for an hour, and proxies drop idle connections); an empty `{}` is sent on removal of the last ticker; and the router is built per call.

```python
"""SSE streaming endpoint for live price updates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .cache import PriceCache

logger = logging.getLogger(__name__)

HEARTBEAT_SECONDS = 15.0  # comment line so proxies do not drop an idle connection


def create_stream_router(price_cache: PriceCache) -> APIRouter:
    """Build a fresh router per call (safe to call twice, e.g. in tests)."""
    router = APIRouter(prefix="/api/stream", tags=["streaming"])

    @router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return router


async def _generate_events(
    price_cache: PriceCache,
    request: Request,
    interval: float = 0.5,
    heartbeat: float = HEARTBEAT_SECONDS,
) -> AsyncGenerator[str, None]:
    """Yield `data:` events when the cache changed, and `: keepalive` when idle."""
    yield "retry: 1000\n\n"

    last_version = -1
    idle = 0.0
    client = request.client.host if request.client else "unknown"
    logger.info("SSE client connected: %s", client)

    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected: %s", client)
                break

            version = price_cache.version
            if version != last_version:
                last_version = version
                prices = price_cache.get_all()
                # An empty dict is still sent, so clients drop tickers that were removed.
                yield f"data: {json.dumps({t: u.to_dict() for t, u in prices.items()})}\n\n"
                idle = 0.0
            elif idle >= heartbeat:
                yield ": keepalive\n\n"
                idle = 0.0

            await asyncio.sleep(interval)
            idle += interval
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled for: %s", client)
        raise
```

Wire format (each event is one line, wrapped here for reading):

```text
retry: 1000

data: {"AAPL": {"ticker": "AAPL", "price": 189.97, "previous_price": 189.99, "timestamp": 1795597216.67,
                "change": -0.02, "change_percent": -0.0105, "direction": "down",
                "prev_close": 190.0, "day_change": -0.03, "day_change_percent": -0.0158},
       "MSFT": {...}}

: keepalive
```

Frontend notes: every event repeats all tickers, including ones that did not change (for example when another ticker is added or removed), so **flash a price only when that ticker's `timestamp` has changed**; key the client state by `ticker`; a ticker absent from an event has been removed; render `day_change_percent === null` as "n/a"; compute flash direction from `direction`, not from colour alone (see `PLAN.md` section 2).

```javascript
const es = new EventSource("/api/stream/prices");
es.onmessage = (e) => setPrices(JSON.parse(e.data));   // whole snapshot: replace, do not merge
```

---

## 10. Application wiring

### 10.1 `tracking.py`: one function keeps the source in sync

Rather than sprinkle `add_ticker`/`remove_ticker` calls (and the ordering questions that come with them), every code path that changes the watchlist or a position calls `reconcile_tickers(source, wanted)`. It is idempotent: it adds what is missing and removes what is no longer needed.

```python
"""Keep the data source's ticker set equal to what the app needs."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from .interface import MarketDataSource, is_valid_symbol, normalize_ticker

logger = logging.getLogger(__name__)

_warned_invalid: set[str] = set()  # warn once per bad symbol, not on every reconcile


async def reconcile_tickers(source: MarketDataSource, wanted: Iterable[str]) -> None:
    """Make `source` track exactly `wanted` (union of every user's watchlist and positions).

    Idempotent, so callers just invoke it after any watchlist or trade change instead of
    reasoning about add/remove ordering.
    """
    want = {normalize_ticker(t) for t in wanted}
    invalid = {t for t in want if not is_valid_symbol(t)}  # sources would silently ignore these
    for ticker in sorted(invalid - _warned_invalid):
        logger.warning("Ignoring invalid ticker symbol %r", ticker)
    _warned_invalid.update(invalid)
    want -= invalid
    have = set(source.get_tickers())
    for ticker in sorted(want - have):
        await source.add_ticker(ticker)
    for ticker in sorted(have - want):
        await source.remove_ticker(ticker)
    if want != have:
        logger.info("Tracked tickers: +%s -%s", sorted(want - have), sorted(have - want))
```

`wanted` comes from the data layer as the union of *all* users' watchlists and open positions (`PLAN.md` section 3), for example:

```python
def all_tracked_tickers() -> set[str]:
    return ({r.ticker for r in query("SELECT ticker FROM watchlist")}
            | {r.ticker for r in query("SELECT ticker FROM positions WHERE quantity > 0")})
```

### 10.2 `main.py` (market-related parts)

`price_cache` is plain in-memory state with no I/O, so it is created at import time, which lets the SSE router be included normally. The source (background tasks, network) is created in the lifespan. `db` functions are the data layer's (`backend/db`, every function taking `user_id`); `get_current_user` is the single place that returns `"default"`.

```python
"""FastAPI wiring for market data (the rest of the app is built around this)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from app import db  # backend/db data layer; every function takes user_id explicitly
from app.deps import get_current_user  # returns "default" today; the only place that does
from app.market import (
    MarketDataError,
    PriceCache,
    create_stream_router,
    normalize_ticker,
    reconcile_tickers,
    start_market_data,
)

# The cache is plain in-memory state with no I/O, so it can exist at import time. That lets
# the SSE router be included normally instead of from inside the lifespan.
price_cache = PriceCache()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init()
    app.state.market = await start_market_data(price_cache, db.all_tracked_tickers())
    yield
    await app.state.market.stop()


app = FastAPI(title="FinAlly", lifespan=lifespan)
app.include_router(create_stream_router(price_cache))


class TickerBody(BaseModel):
    ticker: str


@app.get("/api/health")
async def health(request: Request):
    return {"status": "ok", "market": request.app.state.market.status(), "prices": len(price_cache)}


@app.post("/api/watchlist", status_code=201)
async def add_watchlist(
    body: TickerBody, request: Request, user_id: str = Depends(get_current_user)
):
    market, ticker = request.app.state.market, normalize_ticker(body.ticker)
    try:
        if not await market.validate_ticker(ticker):
            raise HTTPException(404, f"Unknown ticker {ticker}")
    except MarketDataError as err:
        raise HTTPException(503, str(err)) from err
    db.add_watchlist(user_id, ticker)
    await reconcile_tickers(market, db.all_tracked_tickers())
    update = price_cache.get(ticker)  # None for a moment on Massive snapshot mode
    return {"ticker": ticker, "price": update.price if update else None}


@app.delete("/api/watchlist/{ticker}")
async def remove_watchlist(ticker: str, request: Request, user_id: str = Depends(get_current_user)):
    db.remove_watchlist(user_id, normalize_ticker(ticker))
    # all_tracked_tickers() = every user's watchlist UNION every open position, so a
    # ticker that is still held (or watched by someone else) stays subscribed.
    await reconcile_tickers(request.app.state.market, db.all_tracked_tickers())
    return {"status": "ok"}


class TradeBody(BaseModel):
    ticker: str
    quantity: float
    side: str


@app.post("/api/portfolio/trade")
async def trade(body: TradeBody, request: Request, user_id: str = Depends(get_current_user)):
    ticker = normalize_ticker(body.ticker)
    price = price_cache.get_price(ticker)
    if price is None:  # never invent a price
        raise HTTPException(400, f"No price available for {ticker} yet; try again in a moment")
    result = db.execute_trade(user_id, ticker, body.side, body.quantity, price)
    await reconcile_tickers(request.app.state.market, db.all_tracked_tickers())  # sold to zero?
    return result
```

Smoke test result (simulator, with an in-memory stub standing in for `db`):

```text
GET    /api/health                  -> {"status":"ok","market":{"mode":"simulator","degraded":false,...,"tickers":2},"prices":2}
POST   /api/watchlist {" pypl"}     -> 201 {"ticker":"PYPL","price":65.0}
POST   /api/watchlist {"1bad!"}     -> 404 {"detail":"Unknown ticker 1BAD!"}
POST   /api/portfolio/trade (buy 2) -> {"ticker":"PYPL","side":"buy","quantity":2.0,"price":65.0}
DELETE /api/watchlist/PYPL          -> ok; health still reports 3 tickers (PYPL is held, so it stays tracked)
GET    /api/stream/prices           -> retry: 1000 / data: {"AAPL": {... "prev_close": 190.0, "day_change_percent": -0.0158}, ...}
```

LLM chat trades go through the same service functions as the REST routes (`PLAN.md` section 9), so the same cache lookup and `reconcile_tickers` call apply. An unpriceable ticker is rejected by the deterministic validation step before the reviewer is ever called.

### 10.3 Flows

Add a ticker: `validate_ticker` (404 if unknown, 503 if undecidable) -> insert in `watchlist` -> `reconcile_tickers` (simulator seeds the cache instantly; Massive snapshot wakes the poller; Massive end-of-day reads from memory) -> respond with the price if the cache has one, else `null`.

Remove a ticker: delete the row -> `reconcile_tickers`. If any user still holds a position or watches it, it stays subscribed and priced.

Trade: `cache.get_price(ticker)`; `None` -> HTTP 400 "No price available for X yet"; else execute at that price -> `reconcile_tickers` (a full sell may free the ticker).

### 10.4 Server shutdown

An SSE response stays open until the client disconnects, and uvicorn waits for open responses before it runs lifespan shutdown. With a browser tab connected, the server would never exit on its own and `source.stop()` would not run. **Always start uvicorn with a graceful shutdown timeout**, in the Docker `CMD`, the start script and any development command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 3
```

Keep it well under Docker's 10 s stop timeout. `test_stream_http.py` covers this behaviour.

---

## 11. Configuration reference

Only `MASSIVE_API_KEY` and `LLM_MOCK` are required by `PLAN.md` section 5. The rest are optional and have defaults; add them to `.env.example` as comments.

| Variable / parameter | Default | Meaning |
|---|---|---|
| `MASSIVE_API_KEY` | empty | Set and non-empty selects Massive; otherwise the simulator |
| `MARKET_FORCE_SIMULATOR` | false | `true` ignores the key (demos, tests, CI) |
| `MASSIVE_MODE` | `auto` | `auto` (snapshot, fall back to eod on 403), `snapshot`, or `eod` (skips the probe; best for a known free key) |
| `MASSIVE_POLL_INTERVAL` | 15 | Seconds between snapshot polls (minimum 1). Paid: 2 to 15; free keys are not polled (eod mode refreshes hourly) |
| `SIM_SEED` | unset | Non-negative integer: reproducible simulator series (anything else is ignored with a warning) |
| `SimulatorDataSource(update_interval=)` | 0.5 s | Tick cadence |
| `GBMSimulator(dt=)` | 8.48e-8 | Per-tick variance; keep consistent with the interval |
| `GBMSimulator(event_probability=)` | 0.001 | Shock rate; 0 for calm tests |
| `MassiveDataSource(request_timeout=)` | 10 s | Hard deadline per SDK call (`wait_for` adds 5 s of slack) |
| `MassiveDataSource(eod_refresh=)` | 3600 s | End-of-day reload interval |
| `MassiveDataSource(call_gap=)` | 12.5 s | Minimum spacing of end-of-day calls (5 per minute) |
| SSE `interval` / `heartbeat` | 0.5 s / 15 s | Cache check cadence and idle keep-alive |

Never log the API key or any URL containing `apiKey=`. The client sends the key as a Bearer header, and `_safe()` truncates error text.

---

## 12. Testing

Run: `uv run --extra dev pytest -v` (config already has `asyncio_mode = "auto"`). Current results are in `MARKET_DATA_SUMMARY.md`.

### 12.1 Strategy

| Layer | What | File |
|---|---|---|
| Pure functions | timestamp units, quote fallback chain, zero prices, error classification, all against **real SDK models** built with `TickerSnapshot.from_dict(...)` so a wrong field name fails the test (finding 1) | `test_massive_parse.py` |
| Massive source | fake SDK client: snapshot happy path, 403 to eod, forced mode, bad key, 429 backoff and recovery, missing and removed tickers, early poll on add, validation, reconcile | `test_massive_source.py` |
| Contract | the same behaviour for both implementations via a parametrised fixture: populate, idempotent normalised add/remove, double stop, status shape, validation | `test_contract.py` |
| Simulator and the rest | seeded determinism, volatility calibration (about sigma), correlation (0.6 vs 0.3), known and unknown start prices, 10-ticker Cholesky, `prev_close`, SSE events and heartbeat, factory selection, bad-key fallback | `test_design_extras.py` |
| Existing | models, cache, simulator, simulator source, factory (60 tests) keep passing unchanged | existing files |

Delete `tests/market/test_massive.py`: it mocks snapshots with a non-existent `last_trade.timestamp` and cannot detect finding 1.

No live Massive calls in CI. An optional script `backend/scripts/massive_smoke.py` (runs only when `MASSIVE_API_KEY` is set) should print one real snapshot, one single-ticker snapshot, one grouped-daily response and the error body of a deliberately bad request, to settle Section 14.

### 12.2 Test files

The tests live in `backend/tests/market/` and are not copied here, so this document cannot drift from them.

| File | Covers |
|---|---|
| `test_models.py`, `test_cache.py` | `PriceUpdate`, `PriceCache` |
| `test_interface.py` | base-class defaults, `clean_tickers` |
| `test_simulator.py`, `test_simulator_source.py` | GBM maths, the async source, error resilience |
| `test_factory.py` | source selection |
| `test_massive_parse.py`, `test_massive_source.py` | parsing, error classification, the poller against a fake client |
| `test_contract.py` | behaviour both sources share |
| `test_design_extras.py` | `prev_close`, seeding, correlation, SSE generator, bad-key fallback |
| `test_review_fixes.py` | regression tests for review findings |
| `test_stream_http.py` | the SSE route over real uvicorn, including shutdown with a client connected |

Shared helpers are in `helpers.py`; use `wait_until` instead of fixed sleeps.

---

## 13. Implementation checklist

In order; each step leaves the suite green.

1. **Models and cache**: replace `models.py` and `cache.py` (Sections 3 and 4). Existing tests pass unchanged.
2. **Interface**: replace `interface.py` (Section 5); append `KNOWN_PRICES` to `seed_prices.py`.
3. **Simulator**: replace `simulator.py` (Section 6.3).
4. **Massive**: add `massive_parse.py`, replace `massive_client.py`; delete `tests/market/test_massive.py`; add `test_massive_parse.py` and `test_massive_source.py`.
5. **Factory, stream, tracking, `__init__.py`**: Sections 8, 9, 10.1; add `test_contract.py` and `test_design_extras.py`.
6. **App wiring**: Section 10.2 once `backend/db` exists. `/api/health` must report `market.mode`. Start uvicorn with `--timeout-graceful-shutdown` (Section 10.4).
7. **Docs**: update `backend/CLAUDE.md` (new `PriceUpdate` fields, `reconcile_tickers`, `start_market_data`) and `MARKET_DATA_SUMMARY.md`; move the superseded drafts to `archive/`.
8. **Live check** (needs a key, optional): run the smoke script from 12.1 once and resolve Section 14.
9. Run `uv run --extra dev ruff check app/ tests/` and the demo `uv run market_data_demo.py` (it only uses `cache.get_all()`, which is unchanged).

---

## 14. Open items

### 14.1 Known Massive defects (found in review, not yet fixed)

Details and suggested fixes are in `MARKET_DATA_REVIEW.md`. None affects the simulator-only setup.

| Review finding | Defect |
|---|---|
| 3 | With no tickers the startup probe is skipped, so a free or bad key is never detected |
| 6 | The request deadline abandons threads, which can stop the process exiting |
| 7 | End-of-day mode gives up if the newest weekday is refused |
| 8 | End-of-day refresh can publish the wrong daily baseline |
| 9 | Forced `snapshot` mode still switches to end-of-day |
| 10 | Adding a ticker bypasses rate-limit backoff |
| 13 | `MASSIVE_POLL_INTERVAL=nan` is accepted; a bad `MASSIVE_MODE` stops startup; `stop()` keeps the fallback |

The runtime simulator fallback also starts from seed prices rather than the last real prices, so prices jump when it takes over (finding 4).

### 14.2 Needs a live key

Everything marked here could not be confirmed without a live Massive key. The design degrades safely in each case.

- **401 body text** (`"Unknown API Key"`) is from Polygon-era behaviour. If it differs, `classify_error` may report `OTHER` instead of `AUTH`; the effect is a retry loop instead of a fallback to the simulator. Confirm with the smoke script and, if needed, add the real phrase to `massive_parse.py`.
- **Timestamp units** for `updated`, `last_trade.sip_timestamp` and `min.timestamp` are normalised by magnitude, so the unit does not matter, but the *meaning* (exchange time vs SIP time) was not verified.
- **Free-plan grouped daily availability**: assumed to be "previous sessions only". If same-day bars are available after the close, start the lookback at today instead of yesterday (`_refresh_eod`).
- **Grouped daily payload size** (several MB) and latency on the free plan were not measured. If it is slow, raise `request_timeout` for that call.
- **Starter-plan `lastTrade`**: assumed absent, handled by the fallback chain; the production plan may include it.
- **Holidays**: a holiday costs one extra call in end-of-day mode (no holiday calendar is bundled). Within the 5-per-minute limit thanks to `call_gap`.
- **Price-hours realism**: neither source models market hours. The simulator runs 24/7, Massive prices simply stop changing when the market is closed. Both are expected.
- **Persisting the simulator's day baseline** across restarts (so "daily change" does not reset to 0% on every launch) is intentionally left out; add a small `meta` table in `backend/db` if wanted.
