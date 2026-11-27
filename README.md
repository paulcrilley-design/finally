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
MASSIVE_API_KEY=              # leave empty for now (see Status); the simulator is used
LLM_MOCK=false                # true = deterministic mock LLM (testing, no network)
```

## Status

| Component | State |
|---|---|
| Market data: simulator, price cache, SSE | Complete — see `planning/MARKET_DATA_SUMMARY.md` |
| Market data: Massive (real prices) | Not ready — open defects and untested against the live service, so leave `MASSIVE_API_KEY` empty |
| App server, database, health, watchlist, portfolio and trading APIs | Complete |
| Chat API | Planned |
| Frontend | Live watchlist, trading, positions and charts; chat planned |
| Docker and start/stop scripts | Planned |
| Playwright E2E tests | Planned |

## Development

Run the app (from the repository root):

```bash
cd frontend && npm install && npm run build
cd ../backend && uv run uvicorn app.server:app --port 8000 --timeout-graceful-shutdown 3
```

The app is then at <http://localhost:8000>. The root `.env` is loaded without overriding variables already set in your shell. Uvicorn keeps its default bind, so the app is reachable from this machine only.

Health is at <http://localhost:8000/api/health>. Two optional variables change the defaults: `FINALLY_DB_PATH` (database file, default `db/finally.db`) and `FINALLY_STATIC_DIR` (frontend build, default `frontend/out`).

Frontend (from the repository root; Node 22.22.2 or later in 22, 24.15 or later in 24, or 26 and later):

```bash
npm --prefix frontend ci
npm --prefix frontend run test:unit
npm --prefix frontend run lint
npm --prefix frontend run typecheck
```

Backend (from `backend/`):

```bash
uv sync --extra dev                  # includes pytest, ruff and the demo's dependencies
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev market_data_demo.py   # market data demo
```

Once the Docker build lands, the app will run with `scripts/start_mac.sh` and be served at <http://localhost:8000>.

## Documentation

- `planning/PLAN.md` — full project specification (source of truth)
- `planning/OUI_FORMAT.md` — openUI visual standard (logo, colours, fonts, components)
- `planning/MARKET_DATA_SUMMARY.md` — completed market data component
- `planning/archive/MARKET_DATA_REVIEW.md` — latest market data code review and open items
- `planning/PLAN.md` Section 12 — testing strategy (`planning/archive/TEST_PLAN.md` is a template to fill in later)

## License

See `LICENSE`.
