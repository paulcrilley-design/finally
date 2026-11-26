# FinAlly Backend

FastAPI backend for the FinAlly AI Trading Workstation.

## Structure

- `app/` - Application code
  - `market/` - Market data subsystem
    - `models.py` - PriceUpdate dataclass
    - `cache.py` - Thread-safe price cache
    - `interface.py` - MarketDataSource abstract interface
    - `simulator.py` - GBM-based market simulator
    - `massive_client.py` - Massive/Polygon.io API client
    - `massive_parse.py` - Pure parsing helpers for Massive responses
    - `factory.py` - Data source factory and startup fallback
    - `tracking.py` - Keeps the tracked tickers in step with the app
    - `stream.py` - SSE streaming endpoint
    - `seed_prices.py` - Default ticker prices and parameters

- `tests/` - Unit and integration tests
  - `market/` - Market data tests

## Running Tests

```bash
# Install dependencies, including the dev extra (pytest, ruff, rich)
uv sync --extra dev

# Run all tests
uv run --extra dev pytest

# Run with coverage
uv run --extra dev pytest --cov=app --cov-report=html

# Run specific test file
uv run --extra dev pytest tests/market/test_simulator.py

# Run with verbose output
uv run --extra dev pytest -v
```

## Environment Variables

The app reads the process environment; nothing loads `.env` by itself.

- `MASSIVE_API_KEY` - Optional. Leave empty to use the built-in simulator. The Massive path has known defects (see `../planning/MARKET_DATA_REVIEW.md`).
- `SIM_SEED` - Optional non-negative integer for a reproducible simulator.
- `MARKET_FORCE_SIMULATOR` - Optional. `true` ignores any Massive key.

## Development

```bash
# Run linter
uv run --extra dev ruff check .

# Format code
uv run --extra dev ruff format .

# Market data demo
uv run --extra dev market_data_demo.py
```
