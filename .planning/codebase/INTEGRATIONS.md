---
last_mapped_commit: 7dc6485eb92dc2d388eefd949c257a428bdb494f
last_mapped_at: 2026-11-27
---
# External Integrations

**Analysis Date:** 2026-11-27

## Status Note

Only the market-data integrations are implemented. The LLM (OpenRouter/Cerebras), database (SQLite), and deployment integrations are specified in `planning/PLAN.md` but are not yet in the code. Each entry is marked **Implemented** or **Planned**.

## APIs & External Services

**Market data - Massive (formerly Polygon.io): Implemented, opt-in**
- Purpose: real-time-ish stock quotes via REST polling
- SDK/Client: `massive` 2.2.0 (`RESTClient`, `SnapshotMarketType`, `massive.exceptions.AuthError`, `BadResponse`)
- Code: `backend/app/market/massive_client.py` (`MassiveDataSource`), `backend/app/market/massive_parse.py` (pure response parsing and error classification)
- Auth: `MASSIVE_API_KEY` env var
- Selection: used only when `MASSIVE_API_KEY` is non-empty and `MARKET_FORCE_SIMULATOR` is not true (`backend/app/market/factory.py`)
- Mode: `MASSIVE_MODE` = `auto` | `snapshot` | `eod`; poll interval `MASSIVE_POLL_INTERVAL` (default 15 s)
- Rate limit handling: `FREE_TIER_CALL_GAP = 12.5` s in `massive_client.py` (5 requests/min free tier)
- Fallback: if Massive rejects the key, `start_market_data()` in `factory.py` falls back to a degraded simulator
- Status: per `README.md`, not ready for use (open defects in `planning/archive/MARKET_DATA_REVIEW.md`); leave `MASSIVE_API_KEY` empty

**Market data - built-in simulator: Implemented (default)**
- `backend/app/market/simulator.py` (`SimulatorDataSource`) - GBM price generation using `numpy`
- Seed data and per-ticker parameters: `backend/app/market/seed_prices.py` (10 default tickers: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX)
- Deterministic runs: `SIM_SEED` env var
- No network calls

**LLM - OpenRouter -> Cerebras (via LiteLLM): Planned, not implemented**
- Purpose: AI chat that analyses portfolio and proposes/executes trades, with structured outputs; a second LLM reviews proposed actions (PLAN.md Sections 9 and 10)
- Target model: `openrouter/openai/gpt-oss-120b` with Cerebras as inference provider (PLAN.md)
- Client: LiteLLM (planned)
- Auth: `OPENROUTER_API_KEY` env var (`.env.example` marks it required for chat)
- Test mode: `LLM_MOCK=true` returns deterministic responses without network (PLAN.md Section 13)
- Current code: no `openrouter`, `litellm`, or `cerebras` references exist in `backend/app/`, `backend/tests/`, or `backend/market_data_demo.py`
- Procedure reference: PLAN.md instructs using the `cerebras-inference` skill for LiteLLM/OpenRouter calls

**Other third-party services: none in code**
- PLAN.md Section 14 states no analytics, auth providers, hosted databases, or CDN/font dependencies. All assets are to be bundled in the image.

## Data Storage

**Databases:**
- SQLite - Planned
  - Location at runtime: `db/finally.db` (PLAN.md Section 5/11)
  - Schema and seed code: planned under `backend/db/` (directory not present)
  - Initialisation: planned lazy init on FastAPI lifespan startup, creating tables and seeding defaults if missing
  - Client: Python stdlib `sqlite3` (planned; no DB library in `backend/pyproject.toml`)
  - Current state: no database code exists. `backend/db/` is an empty directory in the working tree and is not tracked by git. `db.sqlite3` is git-ignored (`.gitignore` line 61), which is unrelated to the planned `finally.db`.

**Price cache (in-memory, not external):**
- `backend/app/market/cache.py` - `PriceCache`, thread-safe dict guarded by `threading.Lock`, with a monotonic `version` counter used for SSE change detection

**File Storage:**
- Local filesystem only (planned Docker named volume `finally-data` for the SQLite file)

**Caching:**
- In-process price cache only. No Redis or external cache.

## Authentication & Identity

**Auth Provider:**
- None. Single-user, no login (PLAN.md Sections 1 and 5).
- Planned design: a single dependency `get_current_user() -> str` returning `"default"`, so auth can be added later in one place (PLAN.md Section 5). Not yet implemented.

## Monitoring & Observability

**Error Tracking:**
- None detected

**Logs:**
- Python `logging` module, used in `backend/app/market/` (e.g. `massive_client.py`, `stream.py`, `factory.py`). No log configuration or sink is defined in the repo.

**Health check (planned):**
- `GET /api/health` (PLAN.md Section 8 endpoint table) - intended for Docker health checks. `PriceCache`/source `status()` is exposed to it per `backend/CLAUDE.md`. Route not yet found in `backend/app/`.

## CI/CD & Deployment

**Hosting:**
- Planned: local Docker container on developer machines (single container, port 8000). No cloud host configured.

**CI Pipeline:**
- GitHub Actions: `.github/workflows/claude.yml` - runs `anthropics/claude-code-action@v1` on issue/PR comments and reviews containing `@claude`. Uses secret `CLAUDE_CODE_OAUTH_TOKEN` and `id-token: write`. This is a development assistant workflow, not an application deployment pipeline.
- No test or lint CI workflow is tracked.

**Local review tooling:**
- `scripts/run_review.sh` runs `codex exec` (external Codex CLI) to write `planning/REVIEW.md`. Development tooling only.

## Environment Configuration

**Required env vars (current code):**
- None strictly required. `MASSIVE_API_KEY` is optional; absent means simulator.

**Optional env vars (current code):**
- `MASSIVE_API_KEY`, `MARKET_FORCE_SIMULATOR`, `MASSIVE_MODE`, `MASSIVE_POLL_INTERVAL`, `SIM_SEED`

**Required env vars (planned):**
- `OPENROUTER_API_KEY` - required for AI chat

**Optional env vars (planned):**
- `LLM_MOCK` - `false` by default

**Secrets location:**
- Local `.env` file at repo root (git-ignored via `.gitignore` line 138). Template: `.env.example` (tracked, contains placeholders only).
- Not read for this analysis.
- Note: `backend/CLAUDE.md` states nothing loads `.env` automatically. PLAN.md Section 14 (open question 10) notes the unresolved question of whether the backend reads `.env` directly or only via Docker `--env-file`.

## Webhooks & Callbacks

**Incoming:**
- None implemented.
- Planned HTTP surface (PLAN.md Section 8): REST `/api/*` and SSE `GET /api/stream/prices`. These are served to the browser, not third-party webhooks.
- Implemented: `GET /api/stream/prices` (`backend/app/market/stream.py`, text/event-stream). Every event includes all tickers; clients flash only when `timestamp` changes (`backend/CLAUDE.md`).

**Outgoing:**
- Massive REST polling (when enabled) - `backend/app/market/massive_client.py`
- OpenRouter LLM calls (planned only)
- No webhooks sent.

---

*Integration audit: 2026-11-27*
