# Market Data Backend — Summary

**Status (2026-11-27):** The simulator, price cache and SSE stream are in use by the app. The Massive (real data) review findings are fixed, but **that path has never run against the live service**: try it with a real key before relying on it. History is in `archive/MARKET_DATA_REVIEW.md`. The design is in `archive/MARKET_DATA_DESIGN.md`.

## What Was Built

A market data subsystem in `backend/app/market/` (11 modules) providing price simulation and a Massive REST client behind one interface.

### Architecture

```
MarketDataSource (ABC)
├── SimulatorDataSource  →  GBM simulator (default, no API key needed)
└── MassiveDataSource    →  Massive/Polygon.io REST poller (when MASSIVE_API_KEY set)
        │
        ▼
   PriceCache (thread-safe, in-memory, versioned)
        │
        ├──→ SSE stream endpoint (/api/stream/prices)
        ├──→ Portfolio valuation
        └──→ Trade execution
```

### Modules

| File | Purpose |
|------|---------|
| `models.py` | `PriceUpdate`: immutable price, tick change, direction, `prev_close` and daily change |
| `interface.py` | `MarketDataSource` base class, errors, `normalize_ticker`, `clean_tickers` |
| `cache.py` | `PriceCache`: thread-safe store with a version counter for SSE change detection |
| `seed_prices.py` | Seed and known prices, per-ticker drift and volatility, correlation groups |
| `simulator.py` | `GBMSimulator` (correlated Geometric Brownian Motion) and `SimulatorDataSource` |
| `massive_parse.py` | Pure helpers: timestamps, quote extraction, error classification |
| `massive_client.py` | `MassiveDataSource`: snapshot and end-of-day modes, backoff, simulator fallback |
| `factory.py` | `create_market_data_source`, `start_market_data` (falls back if the key is rejected at startup) |
| `stream.py` | `create_stream_router`: SSE endpoint with keep-alive |
| `tracking.py` | `reconcile_tickers`: keeps tracked tickers equal to watchlists plus positions |

### Key Design Decisions

- Both sources implement one interface, and consumers only read the `PriceCache`.
- Correlated moves via Cholesky decomposition: tech 0.6, finance 0.5, everything else 0.3.
- About a 0.1% chance per tick per ticker of a 2 to 5% shock.
- If a Massive key is rejected, a simulator takes over so prices keep moving, and health reports `degraded`.
- SSE rather than WebSockets.

## Test Suite

All market tests pass (`uv run --extra dev pytest tests/market`).

No test talks to the real Massive service.

```bash
cd backend
uv sync --extra dev
uv run --extra dev pytest
uv run --extra dev ruff check .
```

## Demo

```bash
cd backend
uv run --extra dev market_data_demo.py
```

A terminal dashboard of the 10 default tickers with sparklines, direction arrows and an event log. Runs 60 seconds or until Ctrl+C.

## Usage for Downstream Code

```python
from app.market import PriceCache, normalize_ticker, reconcile_tickers, start_market_data

# Startup
cache = PriceCache()
source = await start_market_data(cache, ["AAPL", "GOOGL", "MSFT"])

# Read prices (None means unknown: never substitute a value)
price = cache.get_price(normalize_ticker("aapl"))
all_prices = cache.get_all()

# After any watchlist or trade change
await reconcile_tickers(source, wanted_tickers)

# Shutdown
await source.stop()
```

Run uvicorn with `--timeout-graceful-shutdown 3`, or an open price stream blocks shutdown.
