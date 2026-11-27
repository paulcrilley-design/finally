# Phase 1: Live Market Terminal - Research

**Researched:** 2026-11-27
**Domain:** FastAPI app wiring, stdlib SQLite, SSE client, Next.js static export, openUI styling, Vitest
**Confidence:** MEDIUM-HIGH (backend HIGH, frontend toolchain MEDIUM: current versions are very new and nothing was built)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

The user chose not to discuss this phase ("Just continue the development. nothing to discuss for now"). All decisions below are Claude's defaults and may be changed by the user.

#### Screen layout
- **D-01:** Header with the openUI logo, product name "FinAlly" and the connection indicator; a watchlist panel; a footer saying the money and prices are simulated.
- **D-02:** No placeholder panels for later features. Cash and total value join the header in Phase 2 (PORT-01).
- **D-03:** Page title is "FinAlly | Trading Workstation".

#### Watchlist
- **D-04:** A table: ticker, price, daily change % and direction arrow; prices to 2 decimals.
- **D-05:** Rows in the order tickers were added (seed order). A price not yet received shows "—".
- **D-06:** Flash only when a ticker's `timestamp` changes and its price moved; about 500 ms fade.

#### Connection behaviour
- **D-07:** While disconnected, the last prices stay on screen and the indicator shows the state.
- **D-08:** "Reconnecting" while the browser retries; "disconnected" if the stream is closed or still down after about 10 seconds. The client keeps retrying, recreating the `EventSource` if it closes.
- **D-09:** `GET /api/health` returns app status and market data mode and status (`ok` or `degraded`).

#### Startup and contracts
- **D-10:** The database is created and seeded at startup (FastAPI lifespan), with stdlib `sqlite3`, all six tables from PLAN.md section 7, at `db/finally.db`; the path can be overridden by an environment variable for tests.
- **D-11:** The entry point loads the project-root `.env` without overriding variables already set.
- **D-12:** Before Docker (Phase 5), build the static frontend and run one uvicorn command with `--timeout-graceful-shutdown 3`; the backend serves the export. Document the command.
- **D-13:** The SSE event keeps the existing shape (`PriceUpdate.to_dict()` keyed by ticker). `GET /api/watchlist` returns `{"watchlist": [...]}` in D-05 order, each item using the same field names, with price fields `null` when unknown.
- **D-14:** Frontend unit tests use Vitest and React Testing Library.

#### Design foundation
- **D-15:** Copy the logo, `Logo.tsx` and `OUI_FORMAT.md` with `~/AI_Code_Projects/standards/sync-brand.sh --sync`. Write `globals.css` and `ui.tsx` fresh from `planning/OUI_FORMAT.md`, and derive the favicon from the master logo. The old deleted files are not restored.

### Claude's Discretion
Module layout, component structure, local frontend development workflow, and anything not listed above.

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| APP-01 | User can open `http://localhost:8000` with no login and get the app, with the pages and API served by one process | `create_app` with routers first, `StaticFiles(html=True)` mounted last (Pattern 1); static export (Pattern 4) |
| APP-02 | A health endpoint reports whether the app and market data are working | `source.status()` plus price staleness check (Pattern 3) |
| APP-03 | A fresh start creates the database with $10,000 cash and the 10 default tickers | Schema and gated seed (Pattern 2) |
| APP-05 | User identity comes from one function and every user-owned record carries `user_id` | `get_current_user` dependency; `dependency_overrides` test (Pattern 2) |
| WATCH-01 | User can see watched tickers with live price and daily change % | `/api/watchlist` merged with SSE data (Patterns 3, 5) |
| WATCH-02 | User sees a fading flash and ▲/▼ arrow when a price changes | Pure tick reducer and keyed CSS animation (Pattern 6) |
| WATCH-07 | User can see connection status, and the stream reconnects by itself | `openPriceStream` state machine (Pattern 5) |
| UI-01 | The app follows `planning/OUI_FORMAT.md` | Brand sync, tokens, Fontsource, `ui.tsx` (Pattern 7) |
| UI-03 | Direction and status never by colour alone, AA contrast, visible focus | Computed contrast table, accessibility rules (Pattern 7) |
| OPS-03 | Stopping the app completes cleanly even with price streams open | `--timeout-graceful-shutdown 3`; app-level HTTP test (Pitfall 9) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Sources: `~/AI_Code_Projects/CLAUDE.md`, `./CLAUDE.md`, `./.claude/CLAUDE.md`, `backend/CLAUDE.md`.

- Smallest change that does the job; edit sections, do not rewrite whole files; no unrelated refactoring.
- **Do not start dev servers, Docker or full builds unless the user asks. Run only the relevant tests.** Plans must put `next build` and live-server checks behind a human checkpoint.
- Show only errors and failures from commands. Keep explanations short; explain new concepts briefly.
- If a task looks big, propose a short plan and wait for OK.
- Never commit `.env` or `.claude/settings.local.json`. Commit and push when a piece of work is done.
- Keep each CLAUDE.md under about 6 KB; put detail (API lists, architecture) in `docs/` or README.
- Never edit `~/AI_Code_Projects/standards/`; if a project brand copy differs from the master, tell the user.
- All UI work follows `planning/OUI_FORMAT.md`. The `./CLAUDE.md` line about preserving design files is overridden by `.planning/PROJECT.md` (frontend written fresh; the user has chosen to leave that line as is).
- Backend: `uv`; `uv sync --extra dev`, `uv run --extra dev pytest`, `uv run --extra dev ruff check .`.
- Call `normalize_ticker()` before any price cache lookup; a missing price is never substituted.
- Leave `MASSIVE_API_KEY` empty. Run uvicorn with `--timeout-graceful-shutdown 3`.
- GSD workflow: change files through a GSD command (this phase: `/gsd-execute-phase`).
- Project skill `cerebras` (LLM calls) is not relevant to this phase.
- Python style [VERIFIED: .planning/codebase/CONVENTIONS.md]: ruff line length 100, `from __future__ import annotations`, `X | None`, one `logger = logging.getLogger(__name__)` per module, `%`-style log args, docstrings on public items, `__all__` in package `__init__.py`.

## Summary

The market data package is complete and gives this phase `PriceCache`, `start_market_data`, `create_stream_router` and `normalize_ticker`. What is missing is glue: an app factory with a lifespan, a small SQLite module, two REST routes, a static mount, and a new `frontend/`. The backend needs no new third-party package; `python-dotenv` (already installed through `uvicorn[standard]`) should be declared directly.

The frontend carries the risk. Current npm "latest" versions are very new, and `typescript@latest` is 7.0.2, which breaks `typescript-eslint`; pin `typescript@~6.0`. The repo's root `.gitignore` ignores `lib/` (so `frontend/src/lib/` would silently never be committed, and Tailwind would skip scanning it) and does **not** ignore `node_modules`, `.next`, `out` or `db/finally.db`. Fix `.gitignore` in the first task, before any `npm install` or first server start.

On the client, `EventSource` gives up permanently on a non-200 response, so the stream wrapper must recreate it, and the 10-second "disconnected" timer must not restart on every retry. In tests, jsdom has no `EventSource` (static search) and `next/image` with a Vite-style string import throws in non-production mode, so both need a stub in the test setup.

**Primary recommendation:** Build one vertical slice at a time: gitignore and DB, then app factory and routes, then a hand-written Next.js export showing the table, then live stream, flash and connection status. Do not run `create-next-app`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schema creation and seed | Database / Storage (`backend/db`) | API lifespan calls it | PLAN.md section 3 isolates the data layer |
| Identity | API / Backend | — | One FastAPI dependency |
| Price generation and cache | API / Backend (existing `app.market`) | — | Global, not per user |
| Price streaming | API / Backend | Browser consumes | Existing SSE router |
| Watchlist membership and order | API / Backend | Browser renders | Server owns the list; client filters the shared stream |
| Daily change % | API / Backend | Browser formats | Already in `to_dict()`; never recompute on the client |
| Flash and arrow | Browser / Client | — | Depends on what this client last showed |
| Connection status | Browser / Client | — | Only the browser knows its `EventSource` state |
| Health | API / Backend | — | Reads source status and cache |
| Static pages, fonts, logo | CDN / Static (exported by Next, served by FastAPI) | — | No SSR; one process |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.128.7 installed | API and static serving | Already a dependency [VERIFIED: backend venv] |
| uvicorn[standard] | 0.40.0 installed | Server | Already a dependency [VERIFIED: backend venv] |
| sqlite3 | stdlib (Python 3.12.16) | Persistence | D-10 |
| python-dotenv | 1.2.4 installed | Load root `.env` | Part of the uvicorn `standard` extra [CITED: github.com/kludex/uvicorn docs/installation.md]; declare directly [WARNING: flagged SUS, download count unknown] |
| next | ^16.4.6 | Static export | PLAN.md [WARNING: SUS, too-new] |
| react, react-dom | ^19.3.1 | UI | Next 16 peer range includes `^19.0.0` [VERIFIED: npm registry] |
| typescript | ~6.0.3 | Types | `latest` is 7.0.2; see Pitfall 7 [VERIFIED: npm registry] |
| tailwindcss, @tailwindcss/postcss | ^4.3.5 | Styling | PLAN.md [WARNING: SUS, too-new] |
| @fontsource-variable/manrope, @fontsource-variable/space-grotesk | ^5.3.0 | Self-hosted fonts | OUI_FORMAT section 3 [VERIFIED: npm registry] |

### Supporting (dev)

| Library | Version | Purpose | Tag |
|---------|---------|---------|-----|
| vitest | ^5.1.2 | Test runner (D-14) | [WARNING: SUS, too-new] |
| vite | ^8.4.0 | Peer dependency of vitest and the React plugin | [WARNING: SUS, too-new] |
| @vitejs/plugin-react | ^6.3.0 | JSX in tests; peers `vite ^8` | [WARNING: SUS, too-new] |
| jsdom | ^31.0.1 | DOM; engines `^22.22.2 \|\| ^24.15.0 \|\| >=26.0.0` | [WARNING: SUS, too-new] |
| @testing-library/react, @testing-library/dom | ^16.3.3, ^10.4.2 | Component tests | [VERIFIED: npm registry] |
| @testing-library/jest-dom | ^8.0.0 | DOM matchers; v8 requires vitest 5 | [WARNING: SUS, too-new] |
| eslint, eslint-config-next | ^10.15.0, ^16.4.6 | Lint (`next lint` was removed in Next 16) | [WARNING: SUS, too-new] |
| @types/node, @types/react, @types/react-dom | ^26, ^19, ^19 | Types | node and react [WARNING: SUS, too-new]; react-dom [ASSUMED] name, seam OK |
| pytest, pytest-asyncio, httpx | 9.0.2, 1.3.0, 0.28.1 installed | Backend tests | Already present |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `typescript@~6.0` | TS 7 with aliased `@typescript/typescript6` | Documented by Next, but two compilers for no benefit here |
| Hand-written scaffold | `create-next-app` | Interactive, pulls its own versions and Google font setup that must then be removed |
| `cn` helper | `clsx` | One line of code; no dependency needed |
| Build then serve | `next dev` with API rewrites | See "Local development" below |

**Installation:**
```bash
# backend/
uv add python-dotenv

# frontend/ (package.json written by hand first)
npm install next@^16.4.6 react@^19.3.1 react-dom@^19.3.1 \
  @fontsource-variable/manrope@^5.3.0 @fontsource-variable/space-grotesk@^5.3.0
npm install -D typescript@~6.0.3 tailwindcss@^4.3.5 @tailwindcss/postcss@^4.3.5 \
  @types/node@^26 @types/react@^19 @types/react-dom@^19 \
  vitest@^5.1.2 vite@^8.4.0 @vitejs/plugin-react@^6.3.0 jsdom@^31.0.1 \
  @testing-library/react@^16.3.3 @testing-library/dom@^10.4.2 @testing-library/jest-dom@^8.0.0 \
  eslint@^10.15.0 eslint-config-next@^16.4.6
```

Commit `frontend/package-lock.json` and the updated `backend/uv.lock`. Recharts is not needed until Phase 3.

## Package Legitimacy Audit

Seam: `gsd-tools query package-legitimacy check`. "Published" is the date the seam reported for the release it judged, not the package's age. The seam reported `postinstall: null` for every npm package; `npm view <pkg> scripts.postinstall` was also empty for all except `vite`, which was checked by the seam only.

| Package | Registry | Published | Weekly downloads | Source repo | Verdict | Disposition |
|---------|----------|-----------|------------------|-------------|---------|-------------|
| next | npm | 2026-11-09 | 91.8M | vercel/next.js | SUS (too-new) | Flagged |
| react / react-dom | npm | 2026-10-14 | 269M / 254M | react/react | OK | Approved |
| typescript | npm | 2026-07-08 | 442M | microsoft/TypeScript | OK | Approved |
| tailwindcss / @tailwindcss/postcss | npm | 2026-11-06 | 185M / 59M | tailwindlabs/tailwindcss | SUS (too-new) | Flagged |
| @fontsource-variable/manrope / space-grotesk | npm | 2026-07-19 | 1.5M / 954k | fontsource/font-files | OK | Approved |
| vitest | npm | 2026-11-25 | 190M | vitest-dev/vitest | SUS (too-new) | Flagged |
| vite | npm | 2026-11-26 | 282M | vitejs/vite | SUS (too-new) | Flagged |
| @vitejs/plugin-react | npm | 2026-11-09 | 139M | vitejs/vite-plugin-react | SUS (too-new) | Flagged |
| jsdom | npm | 2026-11-13 | 163M | jsdom/jsdom | SUS (too-new) | Flagged |
| @testing-library/react / dom | npm | 2026-08-27 / 09-13 | 99M / 123M | testing-library | OK | Approved |
| @testing-library/jest-dom | npm | 2026-11-19 | 102M | testing-library/jest-dom | SUS (too-new) | Flagged |
| eslint | npm | 2026-11-13 | 210M | eslint/eslint | SUS (too-new) | Flagged |
| eslint-config-next | npm | 2026-11-09 | 46M | vercel/next.js | SUS (too-new) | Flagged |
| @types/node / @types/react | npm | 2026-11-26 / 25 | 665M / 243M | DefinitelyTyped | SUS (too-new) | Flagged |
| @types/react-dom | npm | 2026-09-09 | 206M | DefinitelyTyped | OK | Approved |
| python-dotenv | PyPI | 2026-10-01 | unknown | theskumar/python-dotenv | SUS (unknown-downloads) | Flagged (already installed transitively) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged [SUS]:** next, tailwindcss, @tailwindcss/postcss, vitest, vite, @vitejs/plugin-react, jsdom, @testing-library/jest-dom, eslint, eslint-config-next, @types/node, @types/react, python-dotenv.

The planner must add a `checkpoint:human-verify` before installing them. Use **one** checkpoint for the whole list, ahead of the install task. All flags are recency or missing-metric signals on long-established projects.

## Architecture Patterns

### System Architecture Diagram

```
uvicorn app.server:app  (load root .env, override=False)
        |
   lifespan: init_db -> tracked tickers (all users) -> start_market_data
        |                      |
        v                      v
  db/finally.db         SimulatorDataSource --every 500 ms--> PriceCache
        |                                                        |
        |   GET /api/watchlist  <-- user_id <-- get_current_user |
        +------------------------+---- join latest price --------+
                                 |        GET /api/health  ------+
                                 |        GET /api/stream/prices +
                                 v                  |
Browser <-- "/" static export (frontend/out)        |
   |                                                v
   +-- fetch watchlist (order, initial values)   EventSource
   |                                                |-- open  -> "connected" (refetch watchlist)
   |                                                |-- error, CONNECTING -> "reconnecting" -(10 s)-> "disconnected"
   |                                                |-- error, CLOSED     -> "disconnected" -(2 s)-> new EventSource
   v                                                v
 watchlist order  +  tick reducer (timestamp changed and price moved?) -> table row, flash, arrow
```

Route order inside the app: `/api/health`, `/api/watchlist`, `/api/stream/prices`, `/api/{path}` 404, then the static mount at `/`.

### Recommended Project Structure

```
backend/
  app/
    server.py          # entry point only: load_dotenv, logging, app = create_app()
    main.py            # create_app(db_path, static_dir): no import side effects
    identity.py        # get_current_user()
    routes/__init__.py, health.py, watchlist.py
  db/__init__.py, database.py          # schema, seed and queries in one module (plan 01-02)
  tests/test_db.py, test_api.py, test_shutdown.py
frontend/
  package.json, next.config.ts, postcss.config.mjs, tsconfig.json,
  eslint.config.mjs, vitest.config.mts, next-env.d.ts (generated, not committed)
  src/app/layout.tsx, page.tsx, globals.css, icon.png
  src/assets/openui-logo.png            # sync-brand.sh
  src/components/Logo.tsx               # sync-brand.sh, do not edit
  src/components/ui.tsx, SiteHeader.tsx, SiteFooter.tsx,
                 ConnectionStatus.tsx, Watchlist.tsx
  src/lib/types.ts, priceStream.ts, ticks.ts, format.ts, useMarket.ts
  src/test/setup.ts, fakeEventSource.ts
```

- `backend/db/` follows PLAN.md sections 3 and 4. It holds only `__pycache__` today. Add it to `[tool.hatch.build.targets.wheel] packages = ["app", "db"]`.
- Do not use `backend/app/services` yet; nothing needs a service layer in this phase.

### Pattern 1: App factory, lifespan, static mount

```python
# backend/app/main.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]

def create_app(db_path: Path | None = None, static_dir: Path | None = None) -> FastAPI:
    db_path = db_path or Path(os.environ.get("FINALLY_DB_PATH") or PROJECT_ROOT / "db" / "finally.db")
    static_dir = static_dir or Path(os.environ.get("FINALLY_STATIC_DIR") or PROJECT_ROOT / "frontend" / "out")
    cache = PriceCache()  # one per app, so tests do not share state

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(db_path)
        source = await start_market_data(cache, tracked_tickers(db_path))
        app.state.source = source
        try:
            yield
        finally:
            await source.stop()

    app = FastAPI(title="FinAlly", lifespan=lifespan)
    app.state.price_cache, app.state.db_path = cache, db_path
    app.include_router(health_router)
    app.include_router(watchlist_router)
    app.include_router(create_stream_router(cache))

    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                   include_in_schema=False)
    def api_not_found(path: str) -> None:
        raise HTTPException(status_code=404)

    if static_dir.is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
    else:
        logger.warning("No frontend build at %s: serving the API only", static_dir)
    return app
```

```python
# backend/app/server.py
load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
logging.basicConfig(level=logging.INFO)  # uvicorn does not configure app loggers
app = create_app()
```

Environment variable names `FINALLY_DB_PATH` and `FINALLY_STATIC_DIR` are discretionary. Phase 5 must set both in the container, because the `parents[2]` default depends on the repo layout.

Verified by in-process probe (FastAPI `TestClient`, no server):
```
GET / 200 text/html
GET /api/health 200 application/json
GET /api/nope 404 text/html            <- without the catch-all, API typos return the HTML 404 page
POST /api/nope 405 application/json
GET /%2e%2e/%2e%2e/etc/hosts 404
missing dir: RuntimeError              <- StaticFiles on a missing directory raises at construction
{'PROBE_EMPTY': '', 'PROBE_SET': 'fromenv', 'PROBE_NEW': 'fromfile', 'PROBE_BLANK': ''}
missing .env returns: False
```
So `load_dotenv(override=False)` keeps variables already set, **including empty ones**, and a missing `.env` is not an error.

### Pattern 2: Schema, seed and identity

Source of truth, quoted from `planning/PLAN.md:224-271` [VERIFIED: planning/PLAN.md:224-271]:

> users_profile: `id` TEXT PRIMARY KEY (default: `"default"`), `cash_balance` REAL (default: `10000.0`), `created_at` TEXT
> watchlist: `id` TEXT PRIMARY KEY (UUID), `user_id` TEXT (default: `"default"`), `ticker` TEXT, `added_at` TEXT; UNIQUE `(user_id, ticker)`
> positions: `id`, `user_id`, `ticker` TEXT, `quantity` REAL, `avg_cost` REAL, `updated_at` TEXT; UNIQUE `(user_id, ticker)`
> trades: `id`, `user_id`, `ticker` TEXT, `side` TEXT (`"buy"` or `"sell"`), `quantity` REAL, `price` REAL, `executed_at` TEXT
> portfolio_snapshots: `id`, `user_id`, `total_value` REAL, `recorded_at` TEXT
> chat_messages: `id`, `user_id`, `role` TEXT (`"user"` or `"assistant"`), `content` TEXT, `actions` TEXT (null for user messages), `created_at` TEXT
> "Add indexes on `user_id` (and `(user_id, recorded_at)` / `(user_id, created_at)` for snapshots and chat)"
> Seed: "`id="default"`, `cash_balance=10000.0`"; "AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX"

There is no migration step, so get all six tables right now.

```sql
CREATE TABLE IF NOT EXISTS users_profile (
  id TEXT PRIMARY KEY DEFAULT 'default',
  cash_balance REAL NOT NULL DEFAULT 10000.0,
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS watchlist (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default',
  ticker TEXT NOT NULL, added_at TEXT NOT NULL, UNIQUE (user_id, ticker));
CREATE TABLE IF NOT EXISTS positions (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default', ticker TEXT NOT NULL,
  quantity REAL NOT NULL, avg_cost REAL NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE (user_id, ticker));
CREATE TABLE IF NOT EXISTS trades (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default', ticker TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
  quantity REAL NOT NULL, price REAL NOT NULL, executed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default',
  total_value REAL NOT NULL, recorded_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS chat_messages (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL DEFAULT 'default',
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL, actions TEXT, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist (user_id);
CREATE INDEX IF NOT EXISTS idx_positions_user ON positions (user_id);
CREATE INDEX IF NOT EXISTS idx_trades_user ON trades (user_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_user_time ON portfolio_snapshots (user_id, recorded_at);
CREATE INDEX IF NOT EXISTS idx_chat_user_time ON chat_messages (user_id, created_at);
```

`NOT NULL` and `CHECK` are additions to the spec. `users_profile.id` is the user id, so that table has no separate `user_id` column; the verifier should read "every user-owned table carries `user_id`" that way.

```python
@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        with conn:          # commit or rollback; does NOT close
            yield conn
    finally:
        conn.close()

def init_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)   # db/ does not exist in the repo yet
    with connect(path) as conn:
        conn.executescript(SCHEMA)
        seed(conn)          # returns early if the default profile row exists
```

Rules:
- Seed the profile and 10 watchlist rows in one transaction, gated on the absence of the profile row. Never re-seed tickers on later starts (Phase 2 lets the user remove them).
- Watchlist query: `... WHERE user_id = ? ORDER BY added_at, rowid` (seed timestamps can tie).
- Tracked tickers (global, no user filter): `SELECT ticker FROM watchlist UNION SELECT ticker FROM positions`.
- Define `DEFAULT_USER_ID = "default"` in `db/database.py`; `app/identity.py` imports it and exposes `def get_current_user() -> str`. Routes use `Annotated[str, Depends(get_current_user)]`. Every other query function takes `user_id` explicitly.
- DB routes are plain `def` (thread pool). Open and close the connection inside the same function call; do not yield a connection from a dependency into another thread.

### Pattern 3: API contracts

SSE and watchlist item fields, quoted from `backend/app/market/models.py:56-67` [VERIFIED: backend/app/market/models.py:54-67]:
`"ticker"`, `"price"`, `"previous_price"`, `"timestamp"`, `"change"`, `"change_percent"`, `"direction"`, `"prev_close"`, `"day_change"`, `"day_change_percent"`.
`direction` is `'up', 'down', or 'flat'` (`models.py:33`). `timestamp` is Unix seconds (`models.py:16`). `day_change_percent` is `None` without a baseline.

- Watchlist: `cache.get(normalize_ticker(t))`; return `update.to_dict()`, or a dict with `ticker` set and the other nine fields `null`. Daily change % column uses `day_change_percent`, **not** `change_percent` (which is tick to tick).
- Stream behaviour [VERIFIED: backend/app/market/stream.py:17,45,62-67]: first chunk `"retry: 1000\n\n"`, `HEARTBEAT_SECONDS = 15.0`, each `data:` event is a dict of all tracked tickers.
- Simulator status [VERIFIED: backend/app/market/simulator.py:202-208] has keys `"mode"` (`"simulator"`), `"degraded"` (bool), `"degraded_reason"`, `"tickers"`. Other modes (`interface.py:87`): `'simulator', 'massive-snapshot' or 'massive-eod'`.

Recommended health body (D-09), always HTTP 200:
```json
{"status": "ok", "market_data": {"mode": "simulator", "status": "ok", "tickers": 10}}
```
`degraded` when `source.status()["degraded"]` is true, or (simulator mode, tickers > 0) the newest cache timestamp is older than 10 s. `status()` alone does not detect a stalled loop. Top-level `status` follows market data and a `SELECT 1` on the database. Do not echo `degraded_reason`.

### Pattern 4: Next.js static export

```ts
// next.config.ts
const nextConfig: NextConfig = { output: "export", images: { unoptimized: true } };
export default nextConfig;
```
- Output goes to `out/`. Rewrites, redirects, headers, route handlers using the request and server actions do not work with export [CITED: nextjs.org/docs/app/guides/static-exports].
- `postcss.config.mjs`: `{ plugins: { "@tailwindcss/postcss": {} } }` [CITED: tailwindcss.com upgrade guide].
- `export const metadata = { title: "FinAlly | Trading Workstation" }` in `layout.tsx`; `src/app/icon.png` is picked up automatically [CITED: nextjs.org app-icons file convention].
- Components that touch `EventSource` need `"use client"` and create it only inside `useEffect`, with full cleanup (development StrictMode runs effects twice).
- Fetch relative URLs (`/api/watchlist`); same origin, no CORS.
- `tsconfig.json`: strict, `moduleResolution: "bundler"`, `jsx: "react-jsx"`, `paths: {"@/*": ["./src/*"]}` (the sibling `pm/frontend/tsconfig.json` is a working example). Do not copy `pm`'s `next/font/google` use; OUI_FORMAT forbids it.
- Scripts: `dev`, `build`, `lint` (`eslint .`), `typecheck` (`tsc --noEmit`), `test:unit` (`vitest run`).

**Local development (discretion):** keep one workflow in this phase, build then serve; no dev proxy. Document in README (D-12):
```bash
cd frontend && npm install && npm run build
cd ../backend && uv run uvicorn app.server:app --port 8000 --timeout-graceful-shutdown 3
```
If hot reload is wanted later, add rewrites only under `PHASE_DEVELOPMENT_SERVER` and check that the proxy does not buffer SSE [ASSUMED: may need `compress: false`].

### Pattern 5: Stream wrapper and connection state

`EventSource` rules [CITED: html.spec.whatwg.org/multipage/server-sent-events.html]: a non-200 status or wrong content type fails the connection (`CLOSED`, never retried); a network error or ended response reconnects (`CONNECTING`).

```ts
// src/lib/priceStream.ts : framework-free, so fake timers can test it
export function openPriceStream(
  onPrices: (p: PriceMap) => void,
  onStatus: (s: ConnectionStatus) => void,   // "connected" | "reconnecting" | "disconnected"
): () => void {
  let source: EventSource;
  let downTimer: ReturnType<typeof setTimeout> | undefined;
  let retryTimer: ReturnType<typeof setTimeout> | undefined;

  const markDown = () => {
    if (downTimer !== undefined) return;     // never restart the 10 s clock on each retry
    onStatus("reconnecting");
    downTimer = setTimeout(() => onStatus("disconnected"), 10_000);
  };
  const connect = () => {
    source = new EventSource("/api/stream/prices");
    source.onopen = () => {
      clearTimeout(downTimer);
      downTimer = undefined;
      onStatus("connected");
    };
    source.onmessage = (e) => onPrices(JSON.parse(e.data));
    source.onerror = () => {
      markDown();
      if (source.readyState === EventSource.CLOSED) {
        onStatus("disconnected");
        retryTimer = setTimeout(connect, 2_000);
      }
    };
  };
  markDown();       // initial state until the first open
  connect();
  return () => {
    clearTimeout(downTimer);
    clearTimeout(retryTimer);
    source.close();
  };
}
```
- Merge events into state (`{...previous, ...payload}`) so last prices stay while disconnected (D-07). Row order and membership come from `/api/watchlist`.
- Refetch `/api/watchlist` on each `open`; this also covers a failed first fetch.
- The status element is `role="status"` with a dot (`aria-hidden`) plus visible text.

### Pattern 6: Flash and arrow

```ts
// src/lib/ticks.ts
export function nextTick(prev: Tick | undefined, u: PriceUpdate): Tick | undefined {
  if (u.price === null || u.timestamp === null) return prev;
  if (!prev) return { price: u.price, timestamp: u.timestamp, direction: null, flash: 0 };
  if (u.timestamp === prev.timestamp) return prev;                    // repeated event
  if (u.price === prev.price) return { ...prev, timestamp: u.timestamp };
  return { price: u.price, timestamp: u.timestamp,
           direction: u.price > prev.price ? "up" : "down", flash: prev.flash + 1 };
}
```
Compare with the last price this client showed, not `u.direction` (the client can miss ticks). The arrow persists after the fade. Re-trigger the animation by remounting an inner element with `key={tick.flash}`; re-adding the same class does not restart a CSS animation. Apply no flash class while `flash === 0`.

### Pattern 7: openUI styling and accessibility

Tokens, from `planning/OUI_FORMAT.md:37-56` [VERIFIED: planning/OUI_FORMAT.md:37-56]:
```css
@import "tailwindcss";

:root {
  --navy-dark: #263c3d;   --brand-teal-ink: #315f62; --brand-teal: #4c7f82;
  --brand-orange: #d57e39; --brand-orange-ink: #8f4a1b; --gray-text: #666666;
  --surface: #f6f8f7; --surface-strong: #ffffff;
  --stroke: rgba(49, 95, 98, 0.14);
  --shadow: 0 18px 40px rgba(49, 95, 98, 0.12);
}
@theme inline {
  --color-*: initial;                 /* removes default red and green utilities */
  --color-white: #ffffff;
  --color-navy: var(--navy-dark);  --color-teal: var(--brand-teal);
  --color-teal-ink: var(--brand-teal-ink);
  --color-orange: var(--brand-orange); --color-orange-ink: var(--brand-orange-ink);
  --color-gray-text: var(--gray-text); --color-surface: var(--surface);
  --color-surface-strong: var(--surface-strong); --color-stroke: var(--stroke);
  --shadow-panel: var(--shadow);
  --font-sans: "Manrope Variable", "Segoe UI", Calibri, Arial, sans-serif;
  --font-display: "Space Grotesk Variable", "Segoe UI", Arial, sans-serif;
}
body { background: var(--surface); color: var(--navy-dark); font-family: var(--font-sans); }
:focus-visible { outline: 2px solid var(--brand-teal); outline-offset: 2px; }
@keyframes flash-up { from { background-color: color-mix(in srgb, var(--brand-teal-ink) 15%, transparent); } }
@keyframes flash-down { from { background-color: color-mix(in srgb, var(--brand-orange) 15%, transparent); } }
.flash-up { animation: flash-up 500ms ease-out; }
.flash-down { animation: flash-down 500ms ease-out; }
@media (prefers-reduced-motion: reduce) { .flash-up, .flash-down { animation: none; } }
```
`@theme inline` and `--color-*: initial` are documented Tailwind v4 features [CITED: tailwindcss.com/docs/theme, /docs/colors]. Font family names read from the 5.3.0 package CSS: `'Manrope Variable'`, `'Space Grotesk Variable'` [VERIFIED: @fontsource-variable tarball index.css]. In `layout.tsx` import both packages, then `./globals.css`.

Computed WCAG contrast ratios [VERIFIED: local calculation this session]:

| Foreground | white | surface | teal-ink 15% tint | orange 15% tint |
|------------|-------|---------|-------------------|-----------------|
| navy | 11.69 | 10.96 | 9.33 | 10.06 |
| teal-ink | 7.13 | 6.69 | 5.69 | 6.14 |
| orange-ink | 6.64 | 6.22 | 5.30 | 5.71 |
| gray | 5.74 | 5.38 | 4.58 | 4.94 |
| teal (focus) | 4.50 | 4.22 | 3.59 | 3.87 |
| orange (dot) | 3.06 | **2.86** | **2.44** | 2.63 |

- Keep tints at 15% or less (gray falls to 4.37 at 18% teal-ink).
- Orange is never text. The orange "reconnecting" dot passes 3:1 only on white, so keep it in the white header.
- Dots: teal-ink connected, orange reconnecting, orange-ink disconnected (PLAN.md section 2); label in navy or gray.
- Arrow: ▲/▼ `aria-hidden` plus screen-reader text "up"/"down". No `aria-live` on prices.
- Change %: `+0.12%`, `−0.12%` (U+2212), `0.00%` without sign; round before choosing the sign. Teal-ink for gain, orange-ink for loss. `null` shows "—".
- Prices: `Intl.NumberFormat("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2})`, `tabular-nums`, right-aligned.
- Table: `<caption className="sr-only">`, `th scope="col"`, ticker as `th scope="row"`.
- Focus: this read-only screen has almost nothing focusable. Add a "Skip to watchlist" link so visible focus can be demonstrated and tested.
- Layout (OUI section 4): `max-w-[1500px] mx-auto px-6` shared by header, main, footer; header white at 90% with bottom stroke; logo 140 px then "FinAlly" in the display font; panel white, `rounded-3xl`, stroke, `shadow-panel`, 24 px padding; footer gray 12 px with top stroke; no horizontal scroll at phone width.
- `ui.tsx`: write what is used (`cn`, `Panel`, `HEADING`, `SUBHEADING`, `Eyebrow`) plus `Button` per the OUI table; leave `TextField` and `Spinner` to the phase that uses them.

Brand files: run `~/AI_Code_Projects/standards/sync-brand.sh --sync` from the project root. A check run today reported `ok planning/OUI_FORMAT.md` and `missing` for `frontend/src/assets/openui-logo.png` and `frontend/src/components/Logo.tsx` [VERIFIED: script run, check mode]. It does not make a favicon. This crop was tested in the scratchpad and yields the logo's sun "O" alone, 148 x 148:
```bash
sips -c 148 148 --cropOffset 19 1 frontend/src/assets/openui-logo.png --out frontend/src/app/icon.png
```

### Anti-Patterns to Avoid
- Opening `EventSource` per row or per component: one stream per page.
- Seeding with `INSERT OR IGNORE` on every start.
- Mounting static files at `/` before the API routers.
- Pointing `StaticFiles` at the project root (would expose `.env`).
- Editing `Logo.tsx` or the logo locally (brand copies must match the master).
- Raw hex values in components.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE server | New streaming route | `create_stream_router(cache)` | Keep-alive, retry hint and change detection exist and are tested |
| Source startup and fallback | Direct simulator construction | `start_market_data(cache, tickers)` | Handles factory choice and degraded fallback |
| SSE parsing and basic retry | `fetch` stream reader | Native `EventSource` | Only the `CLOSED` case needs code |
| `.env` parsing | Custom parser | `load_dotenv(override=False)` | Quoting and precedence |
| Static file serving | Custom file route | `StaticFiles(html=True)` | Traversal safety, ETags, 404 page |
| Daily change maths | Client calculation | `day_change_percent` | One definition, handles missing baseline |
| Font loading | `@font-face` by hand or Google Fonts | Fontsource packages | Required by OUI |

## Common Pitfalls

### Pitfall 1: Root `.gitignore` hides `frontend/src/lib/` and misses build output
`.gitignore:17` is `lib/` (Python template). `git check-ignore` confirms `frontend/src/lib/priceStream.ts` is ignored, while `frontend/node_modules`, `frontend/out`, `frontend/.next` and `db/finally.db` are **not** ignored [VERIFIED: git check-ignore run]. Tailwind v4 also skips paths listed in `.gitignore` [CITED: tailwindcss.com v4 announcement].
**Avoid:** first task changes `lib/` and `lib64/` to `/backend/lib/` style anchors or removes them, and adds `node_modules/`, `frontend/.next/`, `frontend/out/`, `frontend/coverage/`, `frontend/next-env.d.ts`, `*.tsbuildinfo`, `db/*` with `!db/.gitkeep`. Add `db/.gitkeep`.
**Verify:** `git check-ignore -q frontend/src/lib/types.ts` exits 1; `db/finally.db` exits 0.

### Pitfall 2: Tests picking up the real environment or database
The root `.env` exists and was not read. If it holds a Massive key, startup would use the defective real-data path, and app tests could reach the network.
**Avoid:** tests import `app.main`, never `app.server`; an autouse fixture sets `MARKET_FORCE_SIMULATOR=true` and `FINALLY_DB_PATH` to `tmp_path`. Add a human check that `MASSIVE_API_KEY` is empty.

### Pitfall 3: Static directory missing
Unconditional mount raises `RuntimeError` when `frontend/out` has not been built, breaking every backend test. Mount only if the directory exists and log a warning. API tests use a temporary directory with a stub `index.html`.

### Pitfall 4: Database lifecycle
`with sqlite3.connect()` commits but leaves the connection open (probe confirmed). Connecting fails with `unable to open database file` if the parent directory is missing (probe confirmed). Sharing a connection across threads raises by default [ASSUMED].

### Pitfall 5: Connection status flapping
Restarting the 10 s timer on each `onerror` means "disconnected" never appears (the server asks for 1 s retries). Switching back to "reconnecting" after a recreate is the second variant. Pattern 5 avoids both; test with fake timers.

### Pitfall 6: Test environment gaps
`next/image` throws `missing required "height" property` for a string `src` when `NODE_ENV !== 'production'` [CITED: next v16.4.6 get-img-props.ts]; `Logo` passes only `width`, and Vitest imports PNGs as strings [ASSUMED]. jsdom 31.0.1: zero occurrences of `EventSource` in the package contents (static search, not run) [ASSUMED it is unimplemented]. Stub both in `src/test/`.

### Pitfall 7: `npm install typescript` gives 7.x
`eslint-config-next` needs the TypeScript 6 API; installing 7 as `typescript` makes ESLint configuration loading fail [CITED: nextjs.org/docs/app/api-reference/config/eslint]. `typescript-eslint` 8.74.0 declares `typescript: >=4.8.4 <6.1.0`. Pin `~6.0.3`. npm may print peer warnings because `eslint-plugin-react` 7.37.5 peers stop at ESLint `^9.7`; Next states ESLint 10 is supported, and `pm` uses this pairing. Do not downgrade to ESLint 9 (marked unsupported on npm).

### Pitfall 8: Logo PNG is not transparent
All pixels of the master logo are opaque, background about `#fefefe` [VERIFIED: pixel decode this session], although OUI_FORMAT section 1 says transparent. It is invisible on the white header; do not place it on `surface`. Do not edit the file; tell the user.

### Pitfall 9: What "clean shutdown" looks like
Uvicorn waits `timeout_graceful_shutdown`, cancels remaining tasks, then runs lifespan shutdown [CITED: uvicorn server.py]. So with a tab open, stop takes about 3 s and logs `Cancel 1 running task(s), timeout graceful shutdown exceeded`, which is expected. A cancellation traceback may appear, and the exit status can be non-zero because uvicorn re-raises the signal [ASSUMED for the traceback; re-raise is cited]. Success means the process ends and "Application shutdown complete" is logged. `backend/tests/market/test_stream_http.py` already shows how to test this in-process on port 0; repeat it against `create_app`. Never test the SSE route with `TestClient` (the stream does not end).

### Pitfall 10: Verification needs a build and a server
Project rules forbid starting them unprompted. Make the end-to-end check (build, run, restart, stop with a tab open) a single human checkpoint at the end.

## Code Examples

### Vitest configuration and setup
```ts
// vitest.config.mts
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "./src") } },
  test: { environment: "jsdom", globals: true, setupFiles: ["./src/test/setup.ts"],
          include: ["src/**/*.test.{ts,tsx}"] },
});
```
```ts
// src/test/setup.ts
import "@testing-library/jest-dom/vitest";
vi.mock("next/image", () => ({
  default: ({ src, priority, unoptimized, ...props }: Record<string, unknown>) =>
    createElement("img", { ...props, src: typeof src === "string" ? src : "logo.png" }),
}));
```
Setup per [CITED: nextjs.org testing/vitest guide; jest-dom README]. A `FakeEventSource` (static `CLOSED = 2`, `readyState`, `onopen`, `onmessage`, `onerror`, `close()`, instance list) is installed with `vi.stubGlobal("EventSource", FakeEventSource)`.

### ESLint
```js
// eslint.config.mjs  [CITED: nextjs.org/docs/app/api-reference/config/eslint]
export default defineConfig([...nextVitals, ...nextTs,
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts", "coverage/**"])]);
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `next lint` | ESLint CLI with flat config (removed in Next 16) | Script is `eslint .` |
| `tailwind.config.js` | CSS `@theme` (v4) | No JS config file |
| TypeScript `latest` = 5.x/6.x | `latest` = 7.0.2 | Must pin 6.0 |
| jest-dom 6/7 | 8.0.0, vitest 5 only | Upgrade both together |
| `vite` pulled in by vitest | vitest 5 lists it as a peer | Declare it |

For Phase 5: PLAN.md section 11 says Node 20 for the Docker build stage; `vitest` 5 (`^22.12.0 || ^24.0.0 || >=26.0.0`) and `jsdom` 31 exclude it, so use Node 22 or 24 there.

`Logo.tsx` uses the `priority` prop, which Next 16 deprecates in favour of `preload` [ASSUMED]. A warning at most; any change belongs in the brand master.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Shutdown may log a cancellation traceback and exit non-zero | Pitfall 9 | Verifier misreads a clean stop |
| A2 | `sqlite3` rejects cross-thread use by default | Pitfall 4 | None if the pattern is followed |
| A3 | Vitest imports PNGs as URL strings | Pitfall 6 | Mock is harmless either way |
| A4 | jsdom has no `EventSource` (static search only) | Pitfall 6 | Stub is harmless either way |
| A5 | `next dev` proxy may need `compress: false` for SSE | Pattern 4 | Not used in this phase |
| A6 | Next 16 deprecates `priority` | State of the Art | Cosmetic |
| A7 | `NEXT_TELEMETRY_DISABLED=1` turns off Next's build telemetry; set it in npm scripts or docs because PLAN.md section 9 says no analytics | Security | Anonymous build telemetry sent |
| A8 | RTL auto-cleanup needs `globals: true` | Code Examples | Leaked DOM between tests |
| A9 | 10 s staleness threshold for health is adequate | Pattern 3 | Tune |
| A10 | `next typegen` creates `next-env.d.ts` without a full build | Validation | Typecheck waits for the checkpoint build |
| A11 | The `globals.css`, `priceStream.ts`, `main.py` and test setup listings are untested sketches | Patterns, Code Examples | Executor adjusts; unit tests catch it |

## Open Questions (RESOLVED)

1. **Is `MASSIVE_API_KEY` empty in the local `.env`?** RESOLVED: Claude does not read the file. The owner checks it in the first end-of-phase human check (plan 01-10, Task 2), where the health check must report mode `simulator`. Backend tests force the simulator, so they do not depend on the answer.
2. **Logo transparency differs from OUI_FORMAT.** RESOLVED: no change in this phase to the master or the copy; the logo sits only on the white header, and plan 01-08 reports the difference to the user in its summary.
3. **Additions beyond the spec** (`NOT NULL`, `CHECK`, API 404 catch-all, skip link). RESOLVED: all four are adopted under CONTEXT.md "Claude's Discretion": the constraints and the catch-all in plan 01-02, the skip link in plan 01-10. The user may drop any of them.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node | Frontend build and tests | Yes | 26.13.0 | — |
| npm (registry reachable) | Install | Yes | 11.20.0 | — |
| uv | Backend | Yes | 0.13.9 | — |
| Python (backend venv) | Backend | Yes | 3.12.16 | — |
| sips | Favicon crop | Yes | 316 | — |
| ImageMagick, Pillow | Not needed | No | — | `sips` |
| Port 8000 | Run | Free at research time | — | `--port` |
| Docker | Phase 5 only | Yes | 29.9.3 | — |
| `sync-brand.sh` | D-15 | Yes | — | — |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 with pytest-asyncio 1.3.0; Vitest 5 (not yet installed) |
| Config file | `backend/pyproject.toml`; `frontend/vitest.config.mts` (Wave 0) |
| Quick run command | `cd backend && uv run --extra dev pytest tests/test_api.py -x -q` ; `cd frontend && npx vitest run src/lib` |
| Full suite command | `cd backend && uv run --extra dev pytest -q && uv run --extra dev ruff check .` ; `cd frontend && npm run test:unit && npm run lint && npm run typecheck` |

`typecheck` before any build needs `next-env.d.ts` for the PNG import type; generate it with `npx next typegen` [ASSUMED command behaviour] or run typecheck after the checkpoint build.

### Phase Requirements to Test Map
| Req ID | Behaviour | Type | Automated Command | File Exists? |
|--------|-----------|------|-------------------|--------------|
| APP-01 | `/` serves index, API wins over static, unknown `/api` is JSON 404 | integration | `uv run --extra dev pytest tests/test_api.py -x` | No, Wave 0 |
| APP-02 | Health shape; degraded on degraded or stale source | integration | same file | No |
| APP-03 | Fresh file gets 6 tables, cash 10000.0, 10 tickers in order; second init changes nothing, removed ticker stays removed | unit | `uv run --extra dev pytest tests/test_db.py -x` | No |
| APP-05 | Owned tables have `user_id`; overriding `get_current_user` yields an empty watchlist | unit and integration | both files | No |
| WATCH-01 | Watchlist order, null price fields; table renders price, change %, "—" | integration and component | pytest; `npx vitest run src/components/Watchlist.test.tsx` | No |
| WATCH-02 | Reducer cases (first, repeat timestamp, unchanged price, up, down); arrow and class rendered | unit and component | `npx vitest run src/lib/ticks.test.ts` | No |
| WATCH-07 | open, error, 10 s, CLOSED recreate, cleanup | unit (fake timers) | `npx vitest run src/lib/priceStream.test.ts` | No |
| UI-01 | Header logo alt "openUI", "FinAlly", footer text; fonts self-hosted | component, plus manual look | `npx vitest run src/components` | No |
| UI-03 | Visible status text and screen-reader direction text; contrast and focus | component, plus manual | same | No |
| OPS-03 | Real uvicorn with open stream exits and runs lifespan shutdown | integration | `uv run --extra dev pytest tests/test_shutdown.py -x` | No |

Manual only (one end-of-phase checkpoint): build and run the documented command; check appearance, flash, keyboard focus and phone width; stop and restart the server with the tab open and watch the states and price recovery; Ctrl+C with the tab open; `curl /api/health`; confirm no requests leave localhost.

### Sampling Rate
- Per task commit: the quick command for the touched side.
- Per wave merge: full suite on both sides (existing market tests must stay green).
- Phase gate: full suite green, then the manual checkpoint.

### Wave 0 Gaps
- [ ] `.gitignore` fix and `db/.gitkeep`
- [ ] `backend/tests/test_db.py`, `test_api.py`, `test_shutdown.py`, with an app fixture (temp DB, temp static dir, simulator forced)
- [ ] `frontend/` toolchain, `vitest.config.mts`, `src/test/setup.ts`, `src/test/fakeEventSource.ts`

## Security Domain

ASVS level 1; block on high.

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No (single user by design) | Identity isolated in `get_current_user` |
| V3 Session Management | No | — |
| V4 Access Control | Minimal | Every query filters by `user_id`; bind to default `127.0.0.1` |
| V5 Input Validation | Little (no user input yet) | Parameterised SQL only; `normalize_ticker` |
| V6 Cryptography | No | — |
| Configuration and secrets | Yes | `.env` ignored, never served, never logged; no secrets in frontend |

| Threat | STRIDE | Mitigation |
|--------|--------|------------|
| SQL injection (later phases reuse this layer) | Tampering | `?` placeholders only |
| Path traversal in static serving | Information disclosure | `StaticFiles`, directory limited to the export (probe returned 404) |
| `.env` or database committed or served | Information disclosure | Pitfall 1; never mount the project root |
| Exposure on the local network | Elevation | No `--host 0.0.0.0` before Docker; Phase 5 should publish `127.0.0.1:8000` |
| Error text leaking through health | Information disclosure | Omit `degraded_reason` |
| XSS | Tampering | React escaping; no `dangerouslySetInnerHTML` |
| Third-party requests and supply chain | Tampering | Self-hosted assets, lockfiles, install checkpoint |
| Cross-site writes (not yet, Phase 2) | Spoofing | No write routes in this phase |

## Sources

### Primary
- Code read this session: `backend/app/market/{stream,models,factory,interface,simulator,cache,tracking,seed_prices,__init__}.py`, `backend/tests/market/test_stream_http.py`, `backend/pyproject.toml`
- `planning/PLAN.md`, `planning/OUI_FORMAT.md`, `backend/CLAUDE.md`, `planning/MARKET_DATA_SUMMARY.md`
- `~/AI_Code_Projects/standards/sync-brand.sh`, `brand/projects.conf`, `brand/Logo.tsx`, logo PNG
- Local probes: static mount, dotenv, sqlite, git check-ignore, contrast, favicon crop; `npm view`
- Sibling `pm/frontend` config files (working reference)

### Secondary (documentation)
- Context7 `/vercel/next.js` (static export, Vitest guide, metadata files), `/tailwindlabs/tailwindcss.com` (theme, colours, source detection), `/kludex/starlette` (StaticFiles), `/kludex/uvicorn` (shutdown, extras)
- nextjs.org: eslint and useTypeScriptCli references
- html.spec.whatwg.org server-sent events; jest-dom README

## Metadata

**Confidence breakdown:**
- Backend: HIGH. Existing code read; behaviour probed.
- Frontend stack: MEDIUM. Versions and peers checked in the registry, nothing installed or built.
- Architecture: HIGH. Follows locked decisions.
- Pitfalls: HIGH for repo findings; MEDIUM for test-environment ones.

**Research date:** 2026-11-27
**Valid until:** 2026-12-11 (npm versions are moving quickly)
