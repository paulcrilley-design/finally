# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a single-user AI trading workstation: it streams live market data, lets the user trade a simulated $10,000 portfolio, and includes a chat assistant that analyses positions and executes trades on request. It is the capstone project of an agentic AI coding course, built entirely by coding agents, and runs from one Docker container at `http://localhost:8000` with no login.

The full specification is `planning/PLAN.md`. This milestone builds everything in it that is not yet built.

## Core Value

The trading terminal works: prices stream live, buys and sells fill correctly, and the portfolio, cash and P&L numbers are right.

## Requirements

### Validated

<!-- Existing code in backend/app/market/, 137 tests passing (planning/MARKET_DATA_SUMMARY.md). Not yet wired into an application. -->

- ✓ Market data simulator (correlated GBM, random shocks, realistic seed prices) — existing
- ✓ One `MarketDataSource` interface with a thread-safe in-memory `PriceCache` — existing
- ✓ SSE price stream router at `GET /api/stream/prices` — existing
- ✓ Ticker reconciliation helper that keeps the tracked set equal to a wanted set — existing

### Active

- [ ] FastAPI application that starts market data, mounts the routes and serves the static frontend, with a health check
- [ ] SQLite database with lazy initialisation and seed data, `user_id` on every user-owned table
- [ ] Market-order buy and sell with validation, positions, cash and trade history
- [ ] Portfolio valuation, unrealised P&L and value snapshots over time
- [ ] Watchlist view, add and remove, kept in step with the tracked tickers
- [ ] AI chat that analyses the portfolio and executes trades and watchlist changes, with a second-model review before anything executes
- [ ] Deterministic LLM mock mode
- [ ] Next.js static frontend: header, watchlist with price flashes and sparklines, main chart, trade bar, positions table, heatmap, P&L chart, chat panel
- [ ] Multi-stage Dockerfile and idempotent macOS/Linux start and stop scripts
- [ ] Backend and frontend unit tests, and Playwright end-to-end tests for the scenarios in PLAN.md section 12

### Out of Scope

- Real market data (Massive) fixes — open defects and never run against the live service; v1 uses the simulator with `MASSIVE_API_KEY` empty
- Login and multi-user accounts — single user today; schema and data access stay multi-user ready
- Limit orders, order book, fees, partial fills — market orders only keeps portfolio maths simple
- Token-by-token chat streaming — a loading indicator is enough with Cerebras speed
- Cloud deployment tooling, docker-compose, Windows `.ps1` scripts — one container and macOS/Linux scripts cover the core build
- Dark theme — openUI is a light theme

## Context

- **Built so far:** only the market data subsystem. There is no app entry point, database, trading, LLM or frontend code. The codebase map is in `.planning/codebase/`.
- **Frontend:** `frontend/` is empty. The earlier design foundation files under `frontend/src/` were deliberately left deleted; the frontend is written fresh to `planning/OUI_FORMAT.md`. This overrides the "preserve existing files" wording in PLAN.md sections 2 and 10 and in the project `CLAUDE.md`. Logo files and `Logo.tsx` come from the master in `~/AI_Code_Projects/standards/brand/` (copied into this repo with `standards/sync-brand.sh`).
- **Open questions:** PLAN.md section 13 (trade validation, error response shape, chat failure handling, snapshot retention, Docker `.env` and volume, API/SSE contracts, frontend test runner) is decided per phase, in the discussion for the phase that needs it. Reviewer fail-open for watchlist-only changes (section 9) is likewise open.
- **Market data integration:** call `normalize_ticker()` before any cache lookup; a missing price means reject the trade. Simulator prices reset on restart, which will show as a P&L jump on saved positions, so portfolio work has to handle it. Other open items are in `.planning/codebase/CONCERNS.md`.
- **Tests folder:** `test/` has leftover untracked `node_modules` and results but no `package.json`; E2E setup starts fresh.
- **Learning project:** the owner is learning to build with Claude Code; explain new concepts briefly.

## Constraints

- **Tech stack**: FastAPI managed with `uv` (Python 3.12+), Next.js + TypeScript static export, Tailwind CSS v4, SQLite, SSE — set by PLAN.md
- **Charts**: Recharts only, including the treemap — one charting dependency
- **LLM**: LiteLLM → OpenRouter → Cerebras, `openrouter/openai/gpt-oss-120b`, structured outputs, via the `cerebras` skill
- **LLM safety**: no trade executes on one model's output alone; deterministic validation, then reviewer, fail closed for trades
- **Token budget**: last 10 messages of history, compact context, small `max_tokens`, no reviewer call without actions, no network in mock mode
- **Design**: `planning/OUI_FORMAT.md` is the single source for logo, colours, typography and components; no red/green, direction never shown by colour alone; fonts self-hosted
- **Dependencies**: OpenRouter is the only required external service; no CDNs, analytics or hosted services
- **Deployment**: one container, one port (8000), SQLite on a volume; uvicorn with `--timeout-graceful-shutdown 3`
- **Layout**: desktop-first, usable on tablet and phone widths
- **Secrets**: `.env` is never committed

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| v1 is all of the unbuilt part of PLAN.md | The plan is the capstone specification | — Pending |
| Trading terminal takes priority over copilot and demo polish | Drives trade-offs when something has to give | — Pending |
| Simulator only; Massive fixes deferred | Avoids work on an optional, defective path | — Pending |
| Done means unit tests plus Playwright E2E | Matches PLAN.md section 12 | — Pending |
| Open questions decided per phase | Each is decided with the context of the phase that needs it | — Pending |
| Frontend written fresh; old design files not restored | Built anew through GSD | — Pending |
| SSE, static export, SQLite, single container | PLAN.md section 3: simplest design that meets the need | — Pending |
| Second-model reviewer for LLM actions | Checks and balances on auto-execution | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-11-27 after initialization*
