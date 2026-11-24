# FinAlly Project Review

Reviewer: `reviewer` subagent (Claude). Date: 2026-11-24.

Scope: CLAUDE.md, planning/*.md (PLAN, OUI_FORMAT, MARKET_DATA_SUMMARY, CDX_REVIEW, TEST_PLAN and others), the backend market code and tests, and the frontend foundation files. No files were modified during the review.

Tests were run with `uv run --extra dev pytest --cov=app`. All 73 tests pass and total coverage is 91%. `stream.py` is at 33%, which matters because SSE is the one integration point with no test.

## Overall

The market-data module is solid and the plan is strong. The main risk is contract ambiguity between PLAN.md and the code that already exists, plus a few specific bugs and gaps listed below. CDX_REVIEW.md covers most plan-level issues well, so this review repeats only the ones it agrees with and adds what CDX_REVIEW.md missed.

## Critical (fix before building on top)

1. **Stream router is a module-level singleton.** `backend/app/market/stream.py:17` creates `router` at import time. `create_stream_router()` (line 20) adds `/prices` to that same object on every call. Two calls, such as one per test app or per `create_app()`, register the route twice, and the second one closes over the first call's cache. Fix: build `APIRouter(...)` inside the factory. Add a test that calls the factory twice.

2. **The SSE contract in PLAN.md Section 6 contradicts the implementation.**
   - PLAN.md says each event carries one ticker. `stream.py:81-83` sends one event holding a dict of every ticker, emitted only when `cache.version` changes.
   - The frontend agent will code against the PLAN wording. Document the real shape with an example, the timestamp units (Unix seconds as a float, per `models.py:16`) and the field list.
   - Add a heartbeat comment line. With Massive polling every 15 s, or the market closed, no events flow. Proxies and the "connected" indicator then can't tell a quiet stream from a dead one.
   - A stream that has had no change for N seconds should also emit something so the UI can detect staleness.

3. **Ticker lifecycle is undefined, and the code makes it dangerous.**
   - `remove_ticker` in both sources also evicts the ticker from the cache (`simulator.py:254`, `massive_client.py:75`).
   - The PLAN's watchlist DELETE would blank the price of a ticker that still has an open position. Valuation, trade execution and the heatmap would then break.
   - Define one reconciler that works from the union of watchlist and positions across all users (PLAN.md Section 3 says this, but nothing implements it).
   - The data sources should not own cache eviction.

4. **Trade execution has no atomicity or concurrency contract.** Validate, update cash, update position, insert the trade row and write the snapshot must happen in one transaction, for example `BEGIN IMMEDIATE`. The same service must serve both REST and chat. The chat path has a long LLM gap between validation and execution, so re-validate inside the transaction. (Agrees with CDX P0 #2.)

5. **API and error response schemas are missing.** PLAN.md Section 8 only lists routes. Backend and frontend are meant to be built in parallel, so they need JSON examples for `/api/portfolio`, `/history`, `/watchlist`, trade success and failure, chat (executed and rejected actions), and a standard error body. Nothing else blocks integration as much as this.

## Important

6. **"Daily change %" can't be computed from the cache.**
   - `PriceUpdate.change_percent` (`models.py:25`) is tick-to-tick, not daily.
   - PLAN.md Section 10 lists a daily change % column in the watchlist panel. The simulator has no previous close.
   - Pick a baseline: simulator session-start price, and Massive `prev_day.close` from the snapshot (which the client already fetches but ignores).
   - Add the baseline to `PriceUpdate` or the cache, and relabel the column "session change" if needed.
   - A related problem: the first update for a ticker has `previous_price == price`, so it reads "flat".

7. **Massive client edge cases** (`massive_client.py`).
   - `snap.last_trade` can be None for illiquid or closed-market tickers. The `AttributeError` is caught per snapshot, but the failure is only logged at warning level and the ticker silently never gets a price.
   - Invalid symbols are silently dropped from the response. The watchlist POST therefore can't tell whether a ticker is valid. Decide how to validate: a one-off snapshot call on add, or reject if there is no price within N seconds.
   - `start()` runs `_poll_once()` before the task exists. A network hang blocks app startup. Add a timeout.
   - `add_ticker` doesn't trigger a poll, so a new ticker waits up to 15 s for its first price. A trade on a freshly added ticker would be rejected with "no price".
   - The default `poll_interval=15` fits the free tier at one call per poll. That is fine only if all tickers go in a single call, which `get_snapshot_all` does.

8. **Unknown-ticker simulator prices are random.** `simulator.py:151` uses `random.uniform(50, 300)`. For the chat example PYPL, this gives a different "price" on each restart, and none of it is realistic. At minimum make it deterministic per symbol (hash-seeded). The simulator also accepts any string, such as `"asdf"`, so the plan needs a ticker validation rule (a format regex plus a known list, or Massive lookup).

9. **Simulator tickers are not normalised.** `GBMSimulator.add_ticker("aapl")` makes a distinct lowercase ticker. Massive uppercases (`massive_client.py:67`) but the simulator does not. Normalise in one place, ideally the API layer.

10. **Cache details.**
    - `cache.py:30` uses `timestamp or time.time()`, so a timestamp of 0 falls through to now. Use `is None`.
    - `version` (line 67) is read without the lock. This is harmless in CPython but inconsistent.
    - Prices are rounded to 2 decimals at the cache (lines 36-37). The portfolio will value at 2-decimal prices, which is fine, but state this as the rule in the plan.
    - Per-update rounding of tiny GBM steps works because the true price is held in the simulator, so there is no issue there.

11. **No tests for streaming.** Add:
    - the router-twice case from item 1;
    - the event format;
    - the empty-cache case (nothing is emitted, `stream.py:80`);
    - disconnect handling.

    Also, `tests/conftest.py` defines an `event_loop_policy` fixture that is deprecated in recent pytest-asyncio and is probably unnecessary with `asyncio_mode = auto`. `MARKET_DATA_SUMMARY.md` says Massive coverage is 56%, but it is now 94%. The summary is stale.

12. **OpenUI conformance issues in the PLAN itself.**
    - Section 2 says the downtick flash is an "orange tint with ▼". OpenUI (OUI_FORMAT.md around line 60) says plain orange is never used for text. Specify the arrow and delta text in orange-ink, with the tint at about 10-15% orange as the background only. The plan already says this for P&L but not for the flash.
    - PLAN Section 10 says "no raw hex values", but the Recharts series colours need hex or `var()` strings. Define a `chartColors` constant that reads the CSS variables (or exports the hex values once) and use it everywhere.
    - The plan lists the header's 1500 px max width but omits the OpenUI header spec (white at 90% opacity with a bottom stroke). Say that, or point to OUI_FORMAT Section 4.
    - Chart text labels must be gray `#666666`. Contrast of gray on white is acceptable. A teal tint on a teal-ink uptick flash needs a contrast check.
    - `Logo.tsx` and `ui.tsx` import `next/link` and `next/image`. With `output: 'export'` you must set `images.unoptimized` (the Logo already passes `unoptimized`) and a `<Link>` needs no server. `ButtonLink` is unused in a single-page app and fine to keep.
    - The "Prelegal" and "pm" references in the `ui.tsx` and `globals.css` comments are stale for this repo. Trim them.
    - `globals.css:37-38` comments say there is no page background, but the plan requires `--surface` as the page background. Add `body { background: var(--surface) }` or set it in layout. Note also that `--surface-strong` is defined but not exposed in `@theme`.

13. **Multi-user readiness, status.**
    - The schema and plan are consistent with the constraint. No data-access code exists yet, so nothing is violated.
    - The plan does not yet say where `user_id` appears in the chat flow, snapshots, or the reviewer. Make `get_current_user()` a FastAPI dependency and have service functions take `user_id` as a required positional parameter (no default).
    - The SSE stream is global, which is consistent with the constraint.
    - `PriceCache.remove()` is global state, so one user removing a ticker affects everyone. This is the same defect as item 3.

14. **Project scaffolding gaps.**
    - `.gitignore` (the Python template) lacks `node_modules/`, `.next/`, `frontend/out/`, `db/finally.db*` (including `-wal` and `-shm`), `test/node_modules`, and Playwright output.
    - No `.env.example` exists, although PLAN says it is committed.
    - The untracked `.claude/agents/` and `planning/CDX_REVIEW.md`, and the deleted `planning/REVIEW.md` in git status, need a decision on what to keep.
    - `frontend/` has no `package.json`, `layout.tsx`, `next.config`, or font imports. `ui.tsx` and `globals.css` reference Fontsource fonts that are not installed. CLAUDE.md says to preserve these files while scaffolding, so scaffold in a temp directory and copy over to avoid `create-next-app` clobbering `globals.css`.
    - `frontend/src/app/globals.css` sets `font-sans`, which overrides the Tailwind default, but `@theme inline` with `"Manrope Variable"` only works if Fontsource's CSS is imported in layout. Add a check for this in the build.

15. **LLM section issues** (adds to CDX #7 and #8).
    - PLAN Section 9 mixes two statements: "no third LLM call is needed" and the older "so the LLM can inform the user". Delete the older one.
    - `action_index` is ambiguous. Define one global list with an index per action, and require exactly one verdict per action.
    - The "fail open for watchlist" decision is left open. Pick fail-closed for everything; it is simpler and safer.
    - Pin the model slug and the provider (`provider: {order: ["cerebras"]}`) in code, not by reference to a skill.
    - Structured output through LiteLLM and OpenRouter with gpt-oss-120b needs a fallback when `json_schema` is unsupported. Test with the real key once and record the result.
    - Dependencies for `litellm`, `pydantic` settings, and SQLite (stdlib `sqlite3`, or `aiosqlite`) are missing from `pyproject.toml`, and `rich` is only used by the demo (move it to dev).
    - `.env` handling: PLAN says the backend reads `.env`, but Docker only gets it via `--env-file`. Pick one. Use `--env-file`.

16. **Docker and deploy.**
    - Named volume `finally-data` versus the `db/` bind mount is inconsistent (CDX #11). Pick the named volume and drop the `db/.gitkeep` talk, or use a bind mount for visibility.
    - The multi-stage plan does not say how the static export is placed in `static/` or that API routes must be mounted before `StaticFiles(html=True)`.
    - Use `npm ci` and `uv sync --frozen`, and add a HEALTHCHECK on `/api/health`.
    - Run as a non-root user.
    - Run uvicorn with one worker only. The in-process simulator and in-memory cache break with more than one worker; state this.

## Minor

17. `MARKET_DATA_SUMMARY.md` says "8 modules, ~500 lines" and 56% Massive coverage; refresh the numbers. `backend/market_data_demo.py` and `rich` are production-dependency baggage.
18. `stream.py:62` sends `retry: 1000`, which is good. Add `id:` fields only if resume is wanted (not needed).
19. `stream.py:86` swallows `CancelledError` without re-raising. Re-raise it so server shutdown is clean.
20. `GBMSimulator` uses global `np.random` and `random`, so tests can't be deterministic per instance. Accept a seed or an `rng` argument. This helps the E2E determinism goal.
21. The simulator `step()` rounds to 2 dp (`simulator.py:116`) and the cache rounds again; harmless duplication.
22. Docs: IDEAS_BACKLOG, TUTORIAL and TEST_PLAN are still templates. TEST_PLAN should be filled in as the work progresses.
23. PLAN Section 13 is reviewer feedback inside the spec. Move resolved items into the body and delete the section when done, so the agents don't treat struck-through items as requirements.
24. Snapshot growth: add retention (for example downsample after 7 days) and cap `/api/portfolio/history` to N points.

## Test coverage summary

- **Done:** models, cache, simulator math and correlation, source lifecycle, factory, and Massive parsing with mocks. All pass.
- **Missing:** SSE stream (33%), concurrency in the cache (threads), any DB, API, portfolio, LLM or frontend tests.
- **Remaining plan items to add to PLAN Section 12:** concurrent trade tests, rollback tests, idempotency replay (CDX #6), reviewer malformed-output tests, startup/persistence tests, a production static-export smoke test, and E2E database isolation (reset endpoint or fresh volume per run).

## Recommended next steps (in order)

1. Fix `stream.py` (router factory, heartbeat, re-raise cancel) and add stream tests (items 1, 2, 11, 19).
2. Add a "Contracts" appendix to PLAN.md: SSE payload, REST schemas, error shape, numeric and rounding rules, daily-change baseline, ticker validation, and the union rule for market tickers (items 2, 3, 5, 6, 8).
3. Build a `TickerRegistry` service and make the data sources stop evicting the cache themselves (items 3, 13).
4. Build the DB layer and transactional trade service with `user_id` everywhere, then the REST routes and lifespan wiring. Add the missing dependencies, `.env.example`, and `.gitignore` entries (items 4, 14, 15).
5. Do LLM chat with mock mode first, then the reviewer, using the pinned provider config (item 15).
6. Scaffold the frontend in a scratch directory and merge it in without overwriting the foundation files. Define the chart colour constants and the flash styling per OpenUI (items 12, 14).
7. Add the Dockerfile, start/stop scripts and Playwright E2E, and fill in TEST_PLAN.md (items 16, 22).

## Key paths

- planning/PLAN.md
- backend/app/market/stream.py
- backend/app/market/massive_client.py
- backend/app/market/simulator.py
- backend/app/market/cache.py
- frontend/src/components/ui.tsx
- frontend/src/app/globals.css
