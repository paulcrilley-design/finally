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

## Run

Needs Docker Desktop. Create a `.env` in the project root (see `.env.example`):

```bash
OPENROUTER_API_KEY=your-key   # required for AI chat
MASSIVE_API_KEY=              # leave empty to use the simulator (see Status)
LLM_MOCK=false                # true = deterministic mock LLM (testing, no network)
```

Write values without quotes or inline comments: Docker reads them literally. Then:

```bash
scripts/start_mac.sh --build --open   # build and run at http://localhost:8000
scripts/stop_mac.sh                   # stop; data stays in the finally-data volume
```

Use `--build` again after code changes. The port is published on `127.0.0.1` only, because the
app has no login.

## Status

| Component | State |
|---|---|
| Market data: simulator, price cache, SSE | Complete — see `planning/MARKET_DATA_SUMMARY.md` |
| Market data: Massive (real prices) | Review findings fixed; never run against the live service (no key yet) |
| Database, portfolio, watchlist and chat APIs | Complete |
| Frontend | Complete |
| Docker and start/stop scripts | Complete |
| Playwright E2E tests | Complete (mock LLM) |

## Development

Backend (from `backend/`):

```bash
uv sync --extra dev                  # includes pytest, ruff and the demo's dependencies
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev market_data_demo.py   # market data demo
```

Frontend (from `frontend/`):

```bash
npm ci
npm test
npm run build    # static export in frontend/out
```

End-to-end tests (from `test/`; they use their own container and volume on port 8010):

```bash
docker build -t finally ..
npm ci && npx playwright install chromium
npx playwright test
```

## Documentation

- `planning/PLAN.md` — full project specification (source of truth)
- `planning/CONTRACTS.md` — API, data layer and test selector contracts
- `planning/OUI_FORMAT.md` — openUI visual standard (logo, colours, fonts, components)
- `planning/MARKET_DATA_SUMMARY.md` — completed market data component
- `planning/archive/MARKET_DATA_REVIEW.md` — latest market data code review and open items
- `planning/PLAN.md` Section 12 — testing strategy (`planning/archive/TEST_PLAN.md` is a template to fill in later)

## License

See `LICENSE`.
