# Phase 1: Live Market Terminal - Context

**Gathered:** 2026-11-27
**Status:** Ready for planning

<domain>
## Phase Boundary

The first runnable app: one FastAPI process that creates and seeds the database, streams simulated prices, and serves a static Next.js page showing the 10 default tickers live in the openUI style. Trading, watchlist editing, charts, chat and Docker belong to later phases.

</domain>

<decisions>
## Implementation Decisions

The user chose not to discuss this phase ("Just continue the development. nothing to discuss for now"). All decisions below are Claude's defaults and may be changed by the user.

### Screen layout
- **D-01:** Header with the openUI logo, product name "FinAlly" and the connection indicator; a watchlist panel; a footer saying the money and prices are simulated.
- **D-02:** No placeholder panels for later features. Cash and total value join the header in Phase 2 (PORT-01).
- **D-03:** Page title is "FinAlly | Trading Workstation".

### Watchlist
- **D-04:** A table: ticker, price, daily change % and direction arrow; prices to 2 decimals.
- **D-05:** Rows in the order tickers were added (seed order). A price not yet received shows "—".
- **D-06:** Flash only when a ticker's `timestamp` changes and its price moved; about 500 ms fade.

### Connection behaviour
- **D-07:** While disconnected, the last prices stay on screen and the indicator shows the state.
- **D-08:** "Reconnecting" while the browser retries; "disconnected" if the stream is closed or still down after about 10 seconds. The client keeps retrying, recreating the `EventSource` if it closes.
- **D-09:** `GET /api/health` returns app status and market data mode and status (`ok` or `degraded`).

### Setup and contracts
- **D-10:** The database is created and seeded at startup (FastAPI lifespan), with stdlib `sqlite3`, all six tables from PLAN.md section 7, at `db/finally.db`; the path can be overridden by an environment variable for tests.
- **D-11:** The entry point loads the project-root `.env` without overriding variables already set.
- **D-12:** Before Docker (Phase 5), build the static frontend and run one uvicorn command with `--timeout-graceful-shutdown 3`; the backend serves the export. Document the command.
- **D-13:** The SSE event keeps the existing shape (`PriceUpdate.to_dict()` keyed by ticker). `GET /api/watchlist` returns `{"watchlist": [...]}` in D-05 order, each item using the same field names, with price fields `null` when unknown.
- **D-14:** Frontend unit tests use Vitest and React Testing Library.

### Design foundation
- **D-15:** Copy the logo, `Logo.tsx` and `OUI_FORMAT.md` with `~/AI_Code_Projects/standards/sync-brand.sh --sync`. Write `globals.css` and `ui.tsx` fresh from `planning/OUI_FORMAT.md`, and derive the favicon from the master logo. The old deleted files are not restored.

### Claude's Discretion
Module layout, component structure, local frontend development workflow, and anything not listed above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Specification
- `planning/PLAN.md` §2-8, §10 - experience, architecture, database schema, API, frontend
- `planning/OUI_FORMAT.md` §1-4 - logo, colours, type, web components

### Market data
- `planning/MARKET_DATA_SUMMARY.md` - usage of the existing subsystem
- `backend/CLAUDE.md` - integration rules

### Project
- `.planning/PROJECT.md` - constraints; frontend is written fresh (overrides "preserve existing files" wording)
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/CONCERNS.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `start_market_data`, `PriceCache`, `reconcile_tickers`, `normalize_ticker` from `app.market`
- `create_stream_router(price_cache)` serves `GET /api/stream/prices`, with `retry: 1000` and 15 s keep-alives

### Established Patterns
- `uv`, pytest with `asyncio_mode = "auto"`, ruff (line length 100)

### Integration Points
- A new FastAPI entry point starts and stops market data in its lifespan, mounts API routes before the static files
- No source exists in `backend/app/{llm,routes,services}` or `backend/db` (only `__pycache__`)

</code_context>

<specifics>
## Specific Ideas

No specific requirements - open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>

---

*Phase: 1-Live Market Terminal*
*Context gathered: 2026-11-27*
