# FinAlly — AI Trading Workstation

FinAlly (Finance Ally) is an AI-powered trading terminal. It streams live market prices, lets you trade a simulated $10,000 portfolio, and includes an LLM chat assistant that can analyze positions and place trades or manage the watchlist for you. It is the capstone project for an agentic AI coding course, built by coding agents.

## Features

- Live prices over SSE for a 10-ticker default watchlist, with flash animations and sparklines
- Market-order trading (buy/sell, instant fill, no fees)
- Portfolio heatmap, P&L chart and positions table
- AI chat assistant. A second LLM reviews every proposed trade before it executes.
- No login. Single user today, with a schema and API designed for multi-user.

## Architecture

One Docker container on port 8000:

- **Frontend:** Next.js (TypeScript, Tailwind v4, Recharts), static export served by FastAPI
- **Backend:** FastAPI managed with `uv`, SQLite at `db/finally.db`
- **Market data:** built-in GBM simulator by default, or the Massive API if `MASSIVE_API_KEY` is set
- **LLM:** LiteLLM → OpenRouter (`gpt-oss-120b` on Cerebras) with structured outputs
- **Styling:** openUI house style, see `planning/OUI_FORMAT.md`

## Configuration

Copy `.env.example` to `.env`:

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | Required for AI chat |
| `MASSIVE_API_KEY` | Optional. Real market data instead of the simulator |
| `LLM_MOCK` | `true` for deterministic mock LLM responses (testing) |

## Running

Planned (the Docker image and scripts are not built yet):

```bash
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
```

Then open http://localhost:8000.

## Project status

| Component | Status |
|---|---|
| Market data (simulator, Massive client, price cache, SSE) | Done, see `backend/README.md` |
| Portfolio, watchlist, chat API and database | To do |
| Frontend | To do (design foundation exists in `frontend/src/`) |
| Docker, start/stop scripts, E2E tests | To do |

## Repository layout

```
backend/    FastAPI uv project (market data complete)
frontend/   Next.js project (design foundation only)
planning/   PLAN.md (spec), OUI_FORMAT.md (design standard), reference docs
scripts/    Helper scripts
test/       Playwright E2E tests (planned)
db/         SQLite volume mount (planned)
```

## Development (backend)

```bash
cd backend
uv sync
uv run pytest
```

See `planning/PLAN.md` for the full specification.

## License

See [LICENSE](LICENSE).
