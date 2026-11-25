# FinAlly — AI Trading Workstation

FinAlly (Finance Ally) is an AI-powered trading terminal that streams live market prices, lets you trade a simulated $10,000 portfolio, and includes an LLM assistant that can analyze positions and execute trades through natural language. It is the capstone project for an agentic AI coding course, built by orchestrated coding agents.

## Features

- Live-streaming watchlist (10 default tickers) with price flashes and sparklines
- Market-order buy/sell with instant fill, no fees
- Portfolio heatmap, P&L chart and positions table
- AI chat that can trade and manage the watchlist, with a second LLM reviewing every proposed action before execution
- Single user, no login; designed so multi-user support needs no schema or API rewrite

## Architecture

One Docker container, one port (8000):

- **Frontend:** Next.js + TypeScript + Tailwind v4 + Recharts, built as a static export and served by FastAPI
- **Backend:** FastAPI (Python, managed with `uv`), REST under `/api/*`, SSE price stream at `/api/stream/prices`
- **Database:** SQLite at `db/finally.db`, lazily initialised and seeded
- **Market data:** built-in GBM simulator by default; Massive (Polygon.io) REST polling if `MASSIVE_API_KEY` is set
- **LLM:** LiteLLM → OpenRouter → Cerebras (`gpt-oss-120b`) with structured outputs

## Configuration

Create a `.env` in the project root:

```bash
OPENROUTER_API_KEY=your-key   # required for AI chat
MASSIVE_API_KEY=              # optional: real market data (simulator if empty)
LLM_MOCK=false                # true = deterministic mock LLM (testing, no network)
```

## Status

| Component | State |
|---|---|
| Market data (simulator, Massive client, price cache, SSE) | Complete — see `planning/MARKET_DATA_SUMMARY.md` |
| Portfolio, watchlist, chat APIs | Planned |
| Frontend | Design foundation only (`frontend/src/`) |
| Docker and start/stop scripts | Planned |
| Playwright E2E tests | Planned |

## Development

Backend (from `backend/`):

```bash
uv sync
uv run pytest
uv run python market_data_demo.py   # market data demo
```

Once the Docker build lands, the app will run with `scripts/start_mac.sh` and be served at <http://localhost:8000>.

## Documentation

- `planning/PLAN.md` — full project specification (source of truth)
- `planning/OUI_FORMAT.md` — openUI visual standard (logo, colours, fonts, components)
- `planning/MARKET_DATA_SUMMARY.md` — completed market data component
- `planning/TEST_PLAN.md` — testing strategy

## License

See `LICENSE`.
