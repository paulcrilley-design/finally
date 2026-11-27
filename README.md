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
- **LLM:** OpenRouter over HTTP → Cerebras (`gpt-oss-120b`) with structured outputs

## Run

With Docker Desktop (or Docker Engine) running, from the repository root:

```bash
scripts/start_mac.sh          # macOS/Linux; add --open to open the browser
scripts/stop_mac.sh
```

The app is then at <http://localhost:8000>, reachable from this machine only. Both scripts are safe to run twice.

- The first start builds the image. After changing code, run `scripts/start_mac.sh --build`.
- Cash, positions, watchlist, trades and chat are kept in the Docker volume `finally-data`, which stopping does not remove. It is separate from `db/finally.db`, used when running without Docker.
- `.env` is mounted read-only into the container, never built into the image. Restart after editing it. On Linux it must be readable by user ID 1000.
- If port 8000 is busy the script says so. `FINALLY_PORT` picks another; `FINALLY_CONTAINER`, `FINALLY_VOLUME`, `FINALLY_IMAGE` and `FINALLY_ENV_FILE` override the other defaults.

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
| AI chat with second-model review | Complete |
| Frontend (desktop first; usable on tablet and phone) | Complete |
| Docker and start/stop scripts | Complete (macOS/Linux) |
| Playwright E2E tests | Complete |

## Development

Run without Docker (from the repository root):

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

End to end (from `test/`; needs Docker):

```bash
npm ci
npx playwright install chromium      # first time only
npm test
```

The tests rebuild the image and run it in mock mode on port 8765 (`E2E_PORT` changes it), with their own container and a volume that is deleted afterwards.

## Documentation

- `planning/PLAN.md` — full project specification (source of truth)
- `planning/OUI_FORMAT.md` — openUI visual standard (logo, colours, fonts, components)
- `planning/MARKET_DATA_SUMMARY.md` — completed market data component
- `planning/archive/MARKET_DATA_REVIEW.md` — latest market data code review and open items
- `planning/PLAN.md` Section 12 — testing strategy (`planning/archive/TEST_PLAN.md` is a template to fill in later)

## License

See `LICENSE`.
