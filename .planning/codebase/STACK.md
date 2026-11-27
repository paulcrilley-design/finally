---
last_mapped_commit: 7dc6485eb92dc2d388eefd949c257a428bdb494f
last_mapped_at: 2026-11-27
---
# Technology Stack

**Analysis Date:** 2026-11-27

## Status Note

The repository is at an early build stage. Only the backend market-data subsystem is implemented. Items below are split into **implemented** (present in the working tree) and **planned** (specified in `planning/PLAN.md` but not yet in the code). Do not assume a planned item exists.

## Languages

**Implemented:**
- Python 3.12+ - all application code in `backend/app/` and `backend/market_data_demo.py` (`requires-python = ">=3.12"` in `backend/pyproject.toml`)

**Planned:**
- TypeScript - frontend (`frontend/`), not yet present
- SQL - SQLite schema under `backend/db/` (directory not present yet)
- Shell - start/stop scripts in `scripts/` (`scripts/start_mac.sh`, `scripts/stop_mac.sh` per PLAN.md; only `scripts/run_review.sh` exists, a Codex review helper)

## Runtime

**Environment:**
- CPython 3.12 or newer (no `.python-version` file present; `.python-version` is commented out in `.gitignore`)
- Node.js: not required yet (the `test/` directory contains Playwright and TypeScript tooling in `test/node_modules/`, but no `test/package.json` is tracked; see Dev Tooling below)

**Package Manager:**
- `uv` (Astral) for Python
  - Lockfile: present - `backend/uv.lock` (version 1, `requires-python >=3.12`)
- npm (implied by `test/node_modules/`): no lockfile tracked for `test/`
- Build backend: Hatchling (`[build-system]` in `backend/pyproject.toml`, wheel packages = `["app"]`)

## Frameworks

**Core (implemented):**
- FastAPI `0.128.7` (locked) - HTTP API and SSE router; `backend/app/market/stream.py` builds an `APIRouter` at `/api/stream` with `GET /api/stream/prices` returning a `StreamingResponse`
- Starlette `0.52.1` (locked, transitive via FastAPI)
- Uvicorn `0.40.0` (locked, with `standard` extras) - ASGI server

**Core (planned, not implemented):**
- Next.js with TypeScript, Tailwind CSS v4, Recharts - frontend, built as a static export (`output: 'export'`) and served by FastAPI (`planning/PLAN.md` Sections 2, 10)
- LiteLLM - LLM access layer, routing via OpenRouter to Cerebras (`openrouter/openai/gpt-oss-120b`) (`planning/PLAN.md` Section 9). No LiteLLM, OpenRouter or Cerebras code exists in `backend/`.

**Testing (implemented, dev extra):**
- pytest `9.0.2` - test runner (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`, `asyncio_mode = "auto"`)
- pytest-asyncio `1.3.0` - async tests
- pytest-cov (version resolved in `backend/uv.lock`) - coverage (`[tool.coverage.*]` in `backend/pyproject.toml`)
- httpx `0.28.1` - FastAPI `TestClient` transport

**Testing (planned):**
- Playwright E2E - `test/node_modules/` contains `@playwright/test` and `playwright-core`; PLAN.md lists Playwright E2E as planned
- Frontend unit tests: Jest or Vitest, not yet decided (PLAN.md Section 14, open question 12)

**Build/Dev:**
- Ruff `0.15.0` - lint and format (`[tool.ruff]`, line-length 100, target py312, rules E, F, I, N, W; E501 ignored)
- Hatchling - build backend
- `uv run` - command runner for tests, lint, and demo

## Key Dependencies

**Critical (runtime, from `backend/pyproject.toml`):**
- `fastapi>=0.115.0` (locked 0.128.7) - API framework and streaming
- `uvicorn[standard]>=0.32.0` (locked 0.40.0) - server; the planned Dockerfile runs it with `--timeout-graceful-shutdown 3`
- `numpy>=2.0.0` (locked 2.4.2) - used by the GBM price simulator (`backend/app/market/simulator.py`)
- `massive>=2.2,<3` (locked 2.2.0) - official Massive (Polygon.io) REST client; imported as `RESTClient`, `SnapshotMarketType`, `AuthError`, `BadResponse` in `backend/app/market/massive_client.py`

**Dev-only (`[project.optional-dependencies] dev`):**
- `rich>=13.0.0` (locked 14.3.2) - terminal dashboard in `backend/market_data_demo.py` only; not used by the app
- `httpx>=0.27.0`, `pytest>=8.3.0`, `pytest-asyncio>=0.24.0`, `pytest-cov>=5.0.0`, `ruff>=0.7.0`

**Standard library notable uses:** `asyncio`, `threading.Lock` (thread-safe `PriceCache` in `backend/app/market/cache.py`), `zoneinfo` (market hours in `backend/app/market/massive_client.py`/`tracking.py`), `dataclasses`, `abc`, `hashlib`, `random`, `logging`.

**Planned (PLAN.md, not yet installed):**
- SQLite via Python stdlib `sqlite3` (or equivalent) - database at `db/finally.db`
- LiteLLM - LLM client
- Recharts, Tailwind CSS v4 - frontend

## Configuration

**Environment variables (read in code):**
- `MASSIVE_API_KEY` - selects Massive data source when non-empty (`backend/app/market/factory.py`)
- `MARKET_FORCE_SIMULATOR` - forces simulator when `1`, `true`, or `yes`
- `MASSIVE_MODE` - `auto` (default), `snapshot`, or `eod`
- `MASSIVE_POLL_INTERVAL` - poll interval in seconds, default 15, minimum 1 (`factory.py`)
- `SIM_SEED` - integer seed for deterministic simulator output (`factory.py`)

**Environment variables (documented, not yet read by code):**
- `OPENROUTER_API_KEY` - required for LLM chat (PLAN.md; present in `.env.example`)
- `LLM_MOCK` - `true` returns deterministic mock LLM responses (PLAN.md; present in `.env.example`)

**Env file:**
- `.env.example` at repo root is the template (tracked). A `.env` file exists at the repo root and is git-ignored (`.gitignore` line 138). Its contents were not read for this analysis.
- Nothing in the backend loads `.env` automatically (`backend/CLAUDE.md`). The app or Docker must supply environment variables (`--env-file .env` per PLAN.md).

**Build/Tooling config files:**
- `backend/pyproject.toml` - project metadata, dependencies, pytest, ruff, coverage
- `backend/uv.lock` - locked dependency graph
- `.github/workflows/claude.yml` - GitHub Action running `anthropics/claude-code-action@v1` on `@claude` mentions
- `scripts/run_review.sh` - runs `codex exec` review of changes since last commit (uses `.claude/.last_review_hash` fingerprint)
- `.gitignore` - ignores `.env`, `.envrc`, `db.sqlite3`, Python build artefacts

**Not present (planned):** `Dockerfile`, `docker-compose` (explicitly removed from plan), `frontend/package.json`, `frontend/tsconfig.json`, `next.config.*`, `backend/db/` schema/seed.

## Platform Requirements

**Development (current):**
- Python 3.12+
- `uv` installed
- Optional: Node.js/npm if working on `test/` Playwright tooling
- Run commands (from `backend/`):
  ```bash
  uv sync --extra dev
  uv run --extra dev pytest
  uv run --extra dev ruff check .
  uv run --extra dev market_data_demo.py
  ```

**Production (planned):**
- Single Docker container, multi-stage build (Node builds Next.js static export, then Python 3.12 slim runs uvicorn) - `planning/PLAN.md` Section 11
- Single port 8000; SQLite file in a named Docker volume `finally-data` mounted at `/app/db` (`planning/PLAN.md` Section 11; open question about named volume vs bind mount)
- Start/stop wrappers `scripts/start_mac.sh` and `scripts/stop_mac.sh` (planned)

---

*Stack analysis: 2026-11-27*
