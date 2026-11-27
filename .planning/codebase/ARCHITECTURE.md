---
last_mapped_commit: 7dc6485eb92dc2d388eefd949c257a428bdb494f
last_mapped_at: 2026-11-27
---
<!-- refreshed: 2026-11-27 -->
# Architecture

**Analysis Date:** 2026-11-27

## Status Summary

FinAlly is partially built. Only the market data subsystem exists as code, in `backend/app/market/`. The planned FastAPI application, REST routes, SQLite layer, LLM integration and Next.js frontend are **planned, not implemented**. Each layer below is marked **[Implemented]** or **[Planned]**.

Sources of truth:
- Implemented: the code under `backend/app/market/` and its tests in `backend/tests/market/`.
- Planned: `planning/PLAN.md` (intended product, sections 3 to 9), summarized by `planning/MARKET_DATA_SUMMARY.md`.

## Pattern Overview

**Overall (intended):** Single-container modular monolith. One FastAPI process serves REST (`/api/*`), an SSE price stream (`/api/stream/*`), and a statically exported Next.js frontend, backed by one SQLite file. [Planned]

**Overall (implemented):** A self-contained Python library-style package, `app`, whose market data subsystem is driven by an asyncio event loop and communicates through a thread-safe in-memory cache. There is no HTTP server entry point yet. [Implemented]

**Key Characteristics:**
- Strategy pattern for market data: an abstract `MarketDataSource` with two interchangeable implementations (`SimulatorDataSource`, `MassiveDataSource`). [Implemented]
- Single shared price cache as the hand-off point between producers (sources) and consumers (SSE stream, later trade logic). [Implemented]
- Global, user-agnostic market data: one cache, one poller, and a ticker set equal to the union of all needs. [Implemented in the market layer; the "union" input is planned]
- Single-user today, with a multi-user design constraint: every user-owned table keeps `user_id`, and identity is resolved in one dependency (`get_current_user()` returning `"default"`). [Planned]

## Layers

**Market Data Model (`backend/app/market/models.py`):** [Implemented]
- Purpose: immutable price snapshot value objects.
- Contains: `PriceUpdate` dataclass with `change`, `change_percent`, `direction`, `day_change`, `to_dict()`.
- Depends on: standard library only.
- Used by: cache, sources, SSE stream.

**Price Cache (`backend/app/market/cache.py`):** [Implemented]
- Purpose: shared, thread-safe store of latest prices keyed by ticker.
- Contains: `PriceCache` guarded by `threading.Lock` (`self._lock`), with a monotonic `version` counter for SSE change detection.
- Depends on: `models.py`.
- Used by: `factory.py`, `simulator.py`, `massive_client.py`, `stream.py`, `tracking.py`.

**Source Abstraction (`backend/app/market/interface.py`):** [Implemented]
- Purpose: the contract all price providers satisfy, plus symbol normalisation and error types.
- Contains: `MarketDataSource` (ABC; `start`, `stop`, `add_ticker`, `remove_ticker`, `get_tickers`, `mode`, `status`, `validate_ticker`), `MarketDataError`, `MarketDataUnavailableError`, `normalize_ticker`, `is_valid_symbol`, `clean_tickers`.
- Depends on: standard library.
- Used by: all sources, `factory.py`, `tracking.py`.

**Data Sources (provider implementations):** [Implemented]
- `backend/app/market/simulator.py`: `GBMSimulator` (pure math, geometric Brownian motion with numpy) and `SimulatorDataSource` (drives it from an `asyncio` task `simulator-loop`). Default source.
- `backend/app/market/massive_client.py`: `MassiveDataSource` polls the Massive (Polygon.io) REST API through `massive.RESTClient`, using `asyncio.to_thread` for blocking calls and an `asyncio.Lock` (`_validate_lock`) to serialise validation. Optional; the README marks it not ready.
- `backend/app/market/massive_parse.py`: pure parsing of Massive responses and error classification (`ErrorKind`, `classify_error`, `extract_quote`).
- `backend/app/market/seed_prices.py`: starting prices and per-ticker volatility/drift parameters.
- Depends on: `cache.py`, `interface.py`, `models.py`. `massive_client.py` also imports `SimulatorDataSource` (used as a degraded fallback).

**Orchestration / Wiring (`backend/app/market/factory.py`, `tracking.py`):** [Implemented]
- Purpose: choose and start the source from environment variables; keep the source's ticker set in sync with the app.
- `create_market_data_source(cache)`: returns `MassiveDataSource` when `MASSIVE_API_KEY` is set and `MARKET_FORCE_SIMULATOR` is not true, else `SimulatorDataSource`.
- `start_market_data(cache, tickers)`: starts the chosen source; on `MarketDataUnavailableError` stops it and starts a degraded simulator.
- `reconcile_tickers(source, wanted)`: idempotent add/remove diff against `source.get_tickers()`.

**Transport (`backend/app/market/stream.py`):** [Implemented]
- Purpose: push cache state to browsers over Server-Sent Events.
- `create_stream_router(price_cache)` returns a fresh `APIRouter` with `GET /api/stream/prices`.
- Polls `price_cache.version` every 0.5 s; emits a full snapshot of all tickers on change; sends `: keepalive` every 15 s when idle.

**HTTP Application / Entry Point:** [Planned]
- No `FastAPI(...)` instance exists in the repository. `start_market_data` and `create_stream_router` are not yet called from any app lifespan.

**Database layer (`backend/db/`):** [Planned]
- The directory exists but is empty of source. PLAN.md specifies SQLite at `db/finally.db`, lazy initialisation and seeding, and isolation so a move to Postgres touches only this module.

**Portfolio, watchlist and trade services, routes, LLM integration (`backend/app/routes/`, `backend/app/services/`, `backend/app/llm/`):** [Planned]
- These directories exist with only `__pycache__` present. PLAN.md section 8 lists the endpoints; section 9 describes LiteLLM to OpenRouter to Cerebras with structured output and a second-opinion review step.

**Frontend (`frontend/`):** [Planned]
- The directory is empty apart from design foundation intended to be placed under `frontend/src/` (per root `CLAUDE.md`). No Next.js project is present.

## Data Flow

### Price Path (implemented)

1. Source is chosen at startup by `create_market_data_source` (`backend/app/market/factory.py`) from env vars.
2. `start_market_data` starts it with the initial tickers. The simulator runs `_run_loop` in an asyncio task; Massive runs a poller task `massive-poller` (`massive_client.py`).
3. Each tick calls `PriceCache.update(ticker, price, timestamp, prev_close)`, which increments `version`.
4. `create_stream_router` endpoint notices the version change and yields one SSE `data:` event containing `{ticker: PriceUpdate.to_dict()}` for every tracked ticker.
5. Clients must flash a price only when its `timestamp` changes (documented in `backend/CLAUDE.md`).

### Ticker Set Reconciliation (implemented; caller planned)

1. After any watchlist or position change, the caller computes the union of all watchlists and open positions.
2. `reconcile_tickers(source, wanted)` in `backend/app/market/tracking.py` normalises, drops invalid symbols, and calls `add_ticker` / `remove_ticker`.

### Trade and Chat Flows (planned)

PLAN.md section 9: user message to LLM (structured output) to second-opinion review to auto-execution against the portfolio in SQLite, with prices from `PriceCache`. Price `None` means reject the trade, never substitute a value (rule in `backend/CLAUDE.md`).

**State Management:**
- Prices: in-memory `PriceCache` (process lifetime), with simulator state in `GBMSimulator`.
- Persistent state: none implemented. SQLite is planned.

## Key Abstractions

**`MarketDataSource`:**
- Purpose: provider-neutral market feed.
- Examples: `backend/app/market/interface.py`, `backend/app/market/simulator.py`, `backend/app/market/massive_client.py`.
- Pattern: abstract base class; lifecycle `start(tickers)` then `add_ticker` / `remove_ticker` then `stop()`.

**`PriceCache` / `PriceUpdate`:**
- Purpose: single source of current prices and their daily-change baseline (`prev_close`, sticky once set).
- Examples: `backend/app/market/cache.py`, `backend/app/market/models.py`.
- Pattern: thread-safe mutable store of immutable snapshots.

**Symbol normalisation:**
- `normalize_ticker()` must be called before any `PriceCache.get()` or `get_price()`; the cache does not normalise (`backend/CLAUDE.md`).

## Entry Points

**Market data demo (implemented):**
- Location: `backend/market_data_demo.py`
- Triggers: `uv run market_data_demo.py` from `backend/`.
- Responsibilities: live terminal dashboard over simulated prices (uses `rich`, a dev-only dependency).

**Test suite (implemented):**
- Location: `backend/tests/` (`conftest.py`, `market/`). `pytest` config lives in `backend/pyproject.toml`.

**Planned application entry:** a FastAPI app (not yet created) that would call `start_market_data` in its lifespan and mount `create_stream_router`, REST routers and static files.

## Architectural Constraints

- **Threading:** Mixed model. Asyncio event loop drives sources and the SSE generator. `PriceCache` uses `threading.Lock`, so it is safe across threads. Blocking Massive SDK calls run in worker threads via `asyncio.to_thread` (`massive_client.py`).
- **Global state:** `_warned_invalid: set[str]` module-level set in `backend/app/market/tracking.py` (warn-once cache). Market data is a process-wide singleton by design (one cache, one poller).
- **Circular imports:** None detected inside `backend/app/market/`. `massive_client.py` imports `simulator.py`, which is one-directional.
- **Startup:** Nothing loads `.env`; the app or Docker must supply environment variables (`backend/CLAUDE.md`). `.env.example` lists `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`.
- **Shutdown:** Uvicorn must use `--timeout-graceful-shutdown 3` or open SSE streams block shutdown (`backend/CLAUDE.md`).
- **Python:** `>=3.12`, packaged with hatchling, wheel contains `app` only (`backend/pyproject.toml`).

## Anti-Patterns

### Calling `PriceCache` with un-normalised symbols

**What happens:** Code passes raw user input straight into `cache.get()` or `get_price()`.
**Why it's wrong:** The cache does not normalise, so lookups miss silently or return the wrong entry.
**Do this instead:** Call `normalize_ticker()` from `backend/app/market/interface.py` first.

### Substituting a price when the cache has none

**What happens:** Code falls back to a default or last-known value when `get_price()` returns `None`.
**Why it's wrong:** Trades would execute at fabricated prices.
**Do this instead:** Treat `None` as unknown and reject the trade (`backend/CLAUDE.md`).

### Relying on the Massive path in development

**What happens:** Developers set `MASSIVE_API_KEY` locally.
**Why it's wrong:** The Massive path has open defects (`planning/archive/MARKET_DATA_REVIEW.md`); the README says to leave the key empty.
**Do this instead:** Use `MARKET_FORCE_SIMULATOR=true` or leave the key unset (`backend/app/market/factory.py`).

## Error Handling

**Strategy:** Typed exceptions in the market layer, with degradation to a simulator rather than failure.

**Patterns:**
- `MarketDataUnavailableError` triggers the simulator fallback in `start_market_data` (`factory.py`), reported later as `degraded` by health status.
- `MassiveCallError` and `classify_error` in `massive_client.py` and `massive_parse.py` categorise provider failures.
- Invalid ticker symbols are logged once and dropped, never raised (`tracking.py`).

## Cross-Cutting Concerns

**Logging:** Standard library `logging`, module-level `logger = logging.getLogger(__name__)` in each module.
**Validation:** Symbol validation via `is_valid_symbol()` in `interface.py`; env parsing with defaults and warnings in `factory.py` (`_env_float`, `_env_seed`).
**Authentication:** None implemented. Planned as a single `get_current_user()` dependency returning `"default"` (PLAN.md section 3).

---

*Architecture analysis: 2026-11-27*
