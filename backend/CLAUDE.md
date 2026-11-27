# Backend — Developer Guide

## Project Setup

```bash
cd backend
uv sync --extra dev   # Install all dependencies including test/lint tools
```

## Market Data API

The market data subsystem lives in `app/market/`. Use these imports:

```python
from app.market import PriceCache, PriceUpdate, MarketDataSource, create_market_data_source
```

### Core Types

- **`PriceUpdate`** — Immutable dataclass: `ticker`, `price`, `previous_price`, `timestamp`, `prev_close` (daily-change baseline, may be `None`), plus properties `change`, `change_percent`, `direction` ("up"/"down"/"flat"), `day_change`, `day_change_percent` (`None` if no baseline), and `to_dict()` for JSON serialization.

- **`PriceCache`** — Thread-safe in-memory store. Key methods:
  - `update(ticker, price, timestamp=None, prev_close=None) -> PriceUpdate` (`prev_close` is sticky)
  - `get(ticker) -> PriceUpdate | None`
  - `get_price(ticker) -> float | None`
  - `get_all() -> dict[str, PriceUpdate]`
  - `remove(ticker)`
  - `version` property — monotonic counter, increments on every update (for SSE change detection)

- **`MarketDataSource`** — Abstract interface implemented by `SimulatorDataSource` and `MassiveDataSource`. Lifecycle: `start(tickers)` -> `add_ticker()` / `remove_ticker()` -> `stop()`.

- **`create_market_data_source(cache)`** — Factory. Returns `MassiveDataSource` if `MASSIVE_API_KEY` is set (and `MARKET_FORCE_SIMULATOR` is not true), otherwise `SimulatorDataSource`.
- **`await start_market_data(cache, tickers)`** — Create and start a source; falls back to a `degraded` simulator if Massive rejects the key. Use this in the app lifespan.
- **`await reconcile_tickers(source, wanted)`** — Idempotently sync the source with the union of all watchlists and open positions. Call after any watchlist or trade change.
- Sources also expose `mode` (`simulator`, `massive-snapshot`, `massive-eod`), `status()` (for `/api/health`) and `await validate_ticker(t)`.
- Optional env: `MASSIVE_MODE` (auto/snapshot/eod), `MASSIVE_POLL_INTERVAL`, `MARKET_FORCE_SIMULATOR`, `SIM_SEED`. Full design: `planning/archive/MARKET_DATA_DESIGN.md`.

### Rules for callers

- `PriceCache` does not normalise symbols: call `normalize_ticker()` before `get()` / `get_price()`.
- A price of `None` means unknown: reject the trade, never substitute a value.
- Sources drop invalid symbols passed to `start()`.
- Nothing loads `.env`; the app or Docker must provide environment variables.
- The Massive path has known defects (`planning/archive/MARKET_DATA_REVIEW.md`); develop with the simulator.

### SSE Streaming

```python
from app.market import create_stream_router

router = create_stream_router(price_cache)  # Returns FastAPI APIRouter
# Endpoint: GET /api/stream/prices (text/event-stream)
```

- Start uvicorn with `--timeout-graceful-shutdown 3`, or an open stream blocks shutdown.
- Every event repeats all tickers: flash a price only when its `timestamp` changes.

### Seed Data

Default tickers: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX. Seed prices and per-ticker volatility/drift params are in `app/market/seed_prices.py`.

## Running Tests

```bash
uv run --extra dev pytest -v              # All tests
uv run --extra dev pytest --cov=app       # With coverage
uv run --extra dev ruff check app/ tests/ # Lint
```

## Demo

```bash
uv run market_data_demo.py   # Live terminal dashboard with simulated prices
```
