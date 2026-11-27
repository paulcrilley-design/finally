# Walking Skeleton — FinAlly

**Phase:** 1
**Generated:** 2026-11-27

## Capability Proven End-to-End

> A trader opens the app served by one FastAPI process and sees the ten tickers seeded in the database with prices updating live.

Delivered by `01-02-PLAN.md`, Task 1 (the tracer), proven end to end on the server side with a page that type-checks. The documented run command follows in `01-03`, page tests in `01-04`, and the real build is checked in `01-10`. The rest of Phase 1 expands that slice.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI on uvicorn, managed with `uv`; app factory `create_app(db_path, static_dir)` in `backend/app/main.py`, entry point `backend/app/server.py` | Existing dependency; a factory with no import side effects keeps tests isolated |
| Frontend framework | Next.js 16 static export (`output: "export"`), React 19, TypeScript 6.0, Tailwind CSS v4 | `planning/PLAN.md` section 3; no server rendering, one origin, no CORS |
| Data layer | SQLite through stdlib `sqlite3`, all data access in `backend/db/`, six tables created and seeded at startup, file `db/finally.db` (override `FINALLY_DB_PATH`) | D-10; keeps a later database swap inside one package |
| Schema changes | No migration step; all six tables exist from the first run | `planning/PLAN.md` section 7 |
| Live data | Existing `app.market` package; Server-Sent Events at `/api/stream/prices`; native `EventSource` in the browser | One-way push is all that is needed |
| API contracts | `GET /api/watchlist` returns `{"watchlist": [...]}` with `PriceUpdate.to_dict()` field names; unknown prices are `null` | D-13; one shape for REST and stream |
| Auth | None. One dependency, `get_current_user()` in `backend/app/identity.py`, returns the default user; every user-owned table has `user_id` | APP-05; adding login later changes one function |
| Static serving | `StaticFiles` over `frontend/out` (override `FINALLY_STATIC_DIR`), mounted after all `/api` routes, with a JSON 404 for unknown `/api` paths | One process serves pages and API |
| Styling | openUI tokens in `frontend/src/app/globals.css`, components in `frontend/src/components/ui.tsx`, self-hosted Fontsource fonts, brand files copied by `sync-brand.sh` | `planning/OUI_FORMAT.md`; D-15 |
| Testing | pytest and ruff (backend); Vitest, React Testing Library, ESLint and `tsc` (frontend) | D-14 |
| Deployment target | Local only in this phase: build the export, then run one uvicorn command with `--timeout-graceful-shutdown 3` on 127.0.0.1:8000. Docker is Phase 5 | D-12 |
| Directory layout | `backend/app/` (API), `backend/db/` (data), `frontend/src/{app,components,lib,test}`, `db/` (runtime database) | `planning/PLAN.md` section 4 |

## Stack Touched in Phase 1

- [ ] Project scaffold — framework and build (01-02); test runner and lint (01-04)
- [ ] Routing — `/` and `/api/watchlist`, `/api/stream/prices` (01-02); `/api/health` (01-05)
- [ ] Database — one real write (seed) and one real read (watchlist) (01-02); guarantees under test (01-03)
- [ ] UI — live watchlist wired to the REST API and the price stream (read-only; the first user input arrives in Phase 2) — 01-02, 01-06, 01-07, 01-09
- [ ] Deployment — documented local full-stack run command in `README.md` — 01-03, 01-10

## Run Command

From the repository root:

1. `cd frontend && npm install && npm run build`
2. `cd ../backend && uv run uvicorn app.server:app --port 8000 --timeout-graceful-shutdown 3`

## Out of Scope (Deferred to Later Slices)

- Buying, selling, positions, cash and total value in the header (Phase 2)
- Adding and removing watchlist tickers (Phase 2)
- Sparklines, ticker chart, heatmap, portfolio value chart (Phase 3)
- AI chat and trade review (Phase 4)
- Docker image, start and stop scripts, tablet and phone layout pass, Playwright tests (Phase 5)
- Real market data through Massive (v2); `MASSIVE_API_KEY` stays empty
- A development server proxy for hot reload; Phase 1 uses build then serve

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- Phase 2: trade and manage the watchlist with correct cash, positions and P&L
- Phase 3: chart prices and the portfolio
- Phase 4: chat with an AI copilot that analyses and trades safely
- Phase 5: start the finished app with one command; data persists; full test suite
