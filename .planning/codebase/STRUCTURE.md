---
last_mapped_commit: 7dc6485eb92dc2d388eefd949c257a428bdb494f
last_mapped_at: 2026-11-27
---
# Codebase Structure

**Analysis Date:** 2026-11-27

## Status

Only `backend/` contains application code, and only the `app/market/` package is implemented. Other top-level areas are placeholders or planned (see notes). The `.claude/` directory is development tooling and is excluded from this map.

## Directory Layout

```
finally/                              # Repository root (git)
├── .env.example                      # Documented env vars (committed; .env is not)
├── .github/workflows/claude.yml      # CI workflow
├── .gitignore
├── CLAUDE.md                         # Project rules for agents
├── LICENSE
├── README.md                         # Product overview and status table
├── backend/                          # Python uv project (implemented in part)
│   ├── app/                          # Application package (hatch wheel target)
│   │   ├── __init__.py               # Package marker (35 bytes)
│   │   ├── market/                   # Market data subsystem [Implemented]
│   │   ├── llm/                      # [Planned] only __pycache__ present
│   │   ├── routes/                   # [Planned] only __pycache__ present
│   │   └── services/                 # [Planned] only __pycache__ present
│   ├── db/                           # [Planned] SQLite schema/seed (empty)
│   ├── tests/                        # pytest suite
│   │   ├── conftest.py
│   │   ├── market/                   # Market tests (implemented)
│   │   ├── api/                      # [Planned] empty
│   │   ├── db/                       # [Planned] empty
│   │   └── llm/                      # [Planned] empty
│   ├── market_data_demo.py           # Rich terminal demo script
│   ├── pyproject.toml                # Dependencies, pytest, ruff, coverage config
│   ├── uv.lock
│   ├── CLAUDE.md                     # Backend developer guide
│   └── README.md
├── frontend/                         # [Planned] empty; design foundation expected in frontend/src/
├── planning/                         # Project documentation for agents
│   ├── PLAN.md                       # Product specification (intended design)
│   ├── MARKET_DATA_SUMMARY.md        # Summary of completed market data work
│   ├── OUI_FORMAT.md                 # UI standard (colours, fonts, components)
│   └── archive/                      # Superseded design docs (read on demand)
├── scripts/
│   └── run_review.sh                 # Review helper script
└── test/                             # [Planned] Playwright E2E
    ├── node_modules/                 # Installed Playwright (git-ignored in intent)
    └── test-results/.last-run.json   # Last-run output
```

Note: `db/` at the repository root (runtime SQLite volume) and `Dockerfile`, `scripts/start_mac.sh`, `scripts/stop_mac.sh` described in PLAN.md section 4 are **not present**.

## Directory Purposes

**`backend/app/market/`:**
- Purpose: market data models, cache, source implementations, wiring, SSE route.
- Contains: `__init__.py` (public API re-exports), `models.py`, `cache.py`, `interface.py`, `simulator.py`, `massive_client.py`, `massive_parse.py`, `seed_prices.py`, `factory.py`, `tracking.py`, `stream.py`.
- Key files: `backend/app/market/__init__.py` (import surface), `backend/app/market/factory.py` (source selection), `backend/app/market/stream.py` (SSE endpoint).

**`backend/tests/market/`:**
- Purpose: unit and HTTP-level tests for the market package.
- Contains: `test_cache.py`, `test_contract.py`, `test_factory.py`, `test_interface.py`, `test_massive_parse.py`, `test_massive_source.py`, `test_models.py`, `test_simulator.py`, `test_simulator_source.py`, `test_stream_http.py`, `test_design_extras.py`, `test_review_fixes.py`, plus `helpers.py` (shared fixtures/builders, not a test module).
- Key files: `backend/tests/conftest.py` (shared fixtures at the tests root).

**`backend/app/llm/`, `backend/app/routes/`, `backend/app/services/`:**
- Purpose (planned): LLM client and prompts; FastAPI routers; business logic for portfolio, watchlist and trades.
- Current contents: `__pycache__` only. Do not assume these are importable packages yet; they have no `__init__.py`.

**`backend/db/`:**
- Purpose (planned): schema SQL, seed data and lazy-init logic, per PLAN.md section 7.
- Current contents: `__pycache__` only.

**`planning/archive/`:**
- Purpose: superseded design and review documents (`MARKET_DATA_DESIGN.md`, `MARKET_SIMULATOR_V2.md`, `MASSIVE_API.md`, `TUTORIAL.md`, etc.).
- Generated: No. Committed: Yes. Read only when the task requires historical detail.

**`test/`:**
- Purpose (planned): Playwright E2E tests that run on the host against the app container.
- Contains: `node_modules/` (Playwright and `@types/node`), `test-results/`. No spec files are tracked.

## Key File Locations

**Entry Points:**
- `backend/market_data_demo.py`: terminal demo (implemented).
- No FastAPI application module exists yet (planned).

**Configuration:**
- `backend/pyproject.toml`: project metadata, dependencies, dev extras, pytest/ruff/coverage settings. Python `>=3.12`, ruff `line-length = 100`.
- `.env.example`: environment variable template (`OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK`). The real `.env` exists locally and must not be read or committed.
- `.gitignore`: ignore rules.

**Core Logic:**
- `backend/app/market/cache.py`: `PriceCache`.
- `backend/app/market/simulator.py`: GBM simulator and simulator source.
- `backend/app/market/massive_client.py`: Massive REST source.
- `backend/app/market/factory.py`: source selection and fallback.
- `backend/app/market/tracking.py`: ticker reconciliation.
- `backend/app/market/stream.py`: SSE route factory.

**Testing:**
- `backend/tests/`: pytest root; `asyncio_mode = "auto"` (set in `pyproject.toml`).
- `test/`: planned Playwright E2E location.

## Naming Conventions

**Files:**
- Python modules: `snake_case.py`, e.g. `massive_parse.py`, `seed_prices.py`.
- Tests: `test_<module or topic>.py` under `backend/tests/<area>/` (matches `python_files = ["test_*.py"]`).
- Planning docs: `UPPERCASE.md`, with `*_V2.md` / `*_REVIEW.md` suffixes for iterations (archived).
- Shell scripts: `snake_case.sh`, e.g. `scripts/run_review.sh`. PLAN.md names `start_mac.sh` / `stop_mac.sh` (planned).

**Directories:**
- Python packages: lowercase single words (`market`, `llm`, `routes`, `services`, `db`, `tests`).
- Test directories mirror app packages: `tests/market/` for `app/market/`.

**Symbols:**
- Classes: `PascalCase`, with a `DataSource` or `Error` suffix where applicable (`SimulatorDataSource`, `MarketDataUnavailableError`).
- Functions: `snake_case`; factories prefixed `create_` (`create_market_data_source`, `create_stream_router`); async lifecycle helpers prefixed `start_` / `reconcile_`.
- Private helpers: leading underscore (`_env_float`, `_generate_events`).
- Module-level loggers: `logger = logging.getLogger(__name__)`.

## Where to Add New Code

**New market data provider:**
- Implementation: `backend/app/market/<provider>_client.py`, subclassing `MarketDataSource` from `backend/app/market/interface.py`.
- Wire it in: branch in `create_market_data_source` in `backend/app/market/factory.py`.
- Export: add to `backend/app/market/__init__.py` `__all__` if public.
- Tests: `backend/tests/market/test_<provider>_*.py`; reuse `backend/tests/market/helpers.py`.

**New FastAPI route (planned API, e.g. portfolio or watchlist):**
- Router: `backend/app/routes/<area>.py`. Add a `backend/app/routes/__init__.py` if the package is to be imported (it is not yet a regular package).
- Business logic: `backend/app/services/<area>.py`.
- Persistence: `backend/db/` (per PLAN.md, data access functions take `user_id`).
- Tests: `backend/tests/api/test_<area>.py`.

**New LLM feature (planned):**
- Client and prompt code: `backend/app/llm/`.
- Tests: `backend/tests/llm/`, using the `LLM_MOCK=true` deterministic mode from PLAN.md section 9.

**New database table or seed data:**
- Schema and seed: `backend/db/` (only this module should know about SQLite, so a move to Postgres is contained).
- Tests: `backend/tests/db/`.

**New frontend component (planned):**
- Source: `frontend/src/` (must reuse the existing design foundation there; do not replace it).
- UI rules: `planning/OUI_FORMAT.md` (read only for UI work).

**Utilities:**
- Market-related helpers: `backend/app/market/interface.py` (symbol functions) or `backend/app/market/models.py`.
- Cross-cutting helpers for other areas: create a module under `backend/app/` rather than inside `market/`.

**New tests for market code:**
- `backend/tests/market/` with `test_*.py` naming and the `async` conventions already set in `pyproject.toml`.

## Special Directories

**`backend/app/*/__pycache__/`, `backend/.pytest_cache/`, `backend/.ruff_cache/`, `backend/.coverage`:**
- Purpose: Python and tool caches.
- Generated: Yes. Committed: No.

**`test/node_modules/`:**
- Purpose: Playwright dependencies.
- Generated: Yes. Committed: No (should be ignored).

**`test/test-results/`:**
- Purpose: Playwright run output.
- Generated: Yes. Committed: Tracked only as `.last-run.json`.

**`backend/.claude/`, `.claude/`:**
- Development tooling, excluded from this analysis.

**`planning/archive/`:**
- Purpose: historical design. Committed: Yes. Read on demand.

---

*Structure analysis: 2026-11-27*
