---
last_mapped_commit: 7dc6485eb92dc2d388eefd949c257a428bdb494f
last_mapped_at: 2026-11-27
---
# Codebase Concerns

**Analysis Date:** 2026-11-27

## Scope and Maturity

The repository currently holds only the market data subsystem (`backend/app/market/`) and its tests. There is no FastAPI `main.py`, no Dockerfile, no frontend application under `frontend/`, no portfolio/trade/LLM code, and no database layer yet. Concerns below cover what exists plus the gaps that will bite once the rest is built.

## Tech Debt

**Committed `node_modules` and test output in git:**
- Issue: 207 files under `test/node_modules/` (Playwright, `@types/node`) are tracked by git, and `test/test-results/.last-run.json` is tracked. `.gitignore` does not exclude them.
- Files: `test/node_modules/**`, `test/test-results/.last-run.json`, `.gitignore`
- Impact: Repository bloat, noisy diffs, and merge conflicts on every dependency change. Generated artefacts make it harder to spot real changes in review.
- Fix approach: `git rm -r --cached test/node_modules test/test-results`, add both to `.gitignore`, commit. Confirm the `test/` directory has a `package.json` that reinstalls them.

**Market data open items from the 2026-11-26 review (verified against current code):**
The review at `planning/archive/MARKET_DATA_REVIEW.md` lists Massive defects. Status checked against `backend/app/market/massive_client.py` on 2026-11-27:
- Finding 1 (snapshot URL): **fixed**. Lines 201 and 255 now pass `SnapshotMarketType.STOCKS.value`.
- Finding 5 (negative `SIM_SEED`): **fixed**. `_env_seed` in `backend/app/market/factory.py` (lines 25-36) rejects negatives.
- Finding 2 (SSE blocks shutdown): **open, not yet applicable**. No `main.py` or start script exists. Must add `--timeout-graceful-shutdown` when the entry point is written (`backend/CLAUDE.md` already documents it).
- Finding 3 (empty watchlist skips probe): **open**. `_poll_snapshot` returns `0` at `backend/app/market/massive_client.py:252-253` and `start()` still records success. A free-tier key therefore never triggers the end-of-day switch, and adding tickers cannot be validated.
- Finding 4 (runtime fallback replaces real prices): **open**. `_fall_back` (`massive_client.py:356-362`) builds a `SimulatorDataSource` on the shared cache without seeding it from cached prices or previous closes, and does not pass `SIM_SEED`. Prices jump at the switch.
- Finding 6 (abandoned threads prevent exit): **open**. `make_client` (`massive_client.py:43-49`) passes `connect_timeout`/`read_timeout` but does not set `connection_pool_kw["timeout"]`, so urllib3 still ignores the deadline. `_call` relies on `asyncio.wait_for`, which abandons the thread.
- Finding 7 (EOD gives up on newest-date 403): **open** (`_refresh_eod`, not re-checked in detail).
- Finding 8 (wrong EOD baseline on rollover): **open** (`prev_close` is sticky in `backend/app/market/cache.py:40-41`; no way to clear it).
- Finding 9 (`MASSIVE_MODE=snapshot` falls back to EOD): **open**. `_run` at `massive_client.py:222-229` checks `self._mode == "snapshot"` but not `self._requested == "auto"`, so a forced snapshot mode can still switch to EOD after the first poll.
- Finding 10 (adds bypass backoff): **open**. `add_ticker` (`massive_client.py:~171`) sets `_wakeup` regardless of `_interval > _base_interval`.
- Findings 11 (symbol validation in `start()`): **fixed** via `clean_tickers`.
- Findings 13 (config edge cases, `nan` poll interval, `stop()` leaving `_fallback` set): **open** (not re-verified line by line).
- Finding 14 (red/green in demo): **open** for `backend/market_data_demo.py`, unless explicitly exempted.
- Impact: The Massive path is untested against the live service. `.env.example` invites users to supply `MASSIVE_API_KEY`, so these defects are reachable.
- Fix approach: Follow the review's recommended order (`planning/archive/MARKET_DATA_REVIEW.md` section 6). Until fixed, keep `MASSIVE_API_KEY` unset in development and document the limitation in `backend/CLAUDE.md` (already present).

**Documentation drift:**
- `planning/archive/MARKET_DATA_DESIGN.md` and `planning/archive/MASSIVE_API.md` still contain the old snapshot call and differ from the code in several listings (review section 5).
- `backend/README.md` module list omits `massive_parse.py` and `tracking.py`.
- Fix approach: Sync design listings with the code when the Massive fixes land.

**Unfinished test scaffolding:**
- `planning/archive/TEST_PLAN.md` is still a template although the root README calls it the testing strategy.

## Known Bugs

**Massive mode cannot start on an empty watchlist:**
- Symptoms: Free key stays in `massive-snapshot`; user cannot add a ticker (403 on validate, no switch to EOD).
- Files: `backend/app/market/massive_client.py:252-253`, `massive_client.py:~171-186` (`start`)
- Trigger: Empty the watchlist and restart with a free-tier key.
- Workaround: Keep at least one ticker, or use `MASSIVE_MODE=eod`.

**Runtime auth failure produces invented prices:**
- Symptoms: Portfolio value jumps to seed-based prices after a key is rejected mid-session.
- Files: `backend/app/market/massive_client.py:356-362`
- Trigger: Key revoked or rejected while the server runs.
- Workaround: None in code. A product decision is needed (see finding 4 in the review).

**Forced snapshot mode can silently switch to EOD:**
- Files: `backend/app/market/massive_client.py:222-229`
- Trigger: `MASSIVE_MODE=snapshot` and a 403 on a later poll.

## Security Considerations

**API key handling:**
- Risk: Key leakage through logs or URLs.
- Files: `backend/app/market/massive_client.py` (`_safe` truncates errors, key sent in header per review)
- Current mitigation: Error text truncated to 200 characters; key is not logged in the market module.
- Recommendations: Keep this discipline for the LLM (OpenRouter) and future portfolio code. Add a test asserting the key never appears in log output.

**Environment loading is not defined:**
- Risk: Nothing loads `.env`; a future app could read secrets inconsistently or commit a real `.env`.
- Files: `.env.example`, `backend/app/market/factory.py` (reads `os.environ` only)
- Current mitigation: `.gitignore` lists `.env`; `.env.example` contains placeholders only.
- Recommendations: Choose one loader (e.g. `python-dotenv` in the entry point), keep `.env` ignored, and verify `git ls-files | grep .env` in CI.

**CI workflow with broad token:**
- Files: `.github/workflows/claude.yml` (grants `id-token: write`, `actions: read`; triggers on any `@claude` comment)
- Risk: Any commenter who can trigger the workflow runs Claude with repository access. Acceptable for a private course repo, but review before making the repository public.
- Recommendations: Restrict triggers to collaborators, or verify `author_association` in the `if:` condition.

## Performance Bottlenecks

**Blocking SDK calls in threads with no socket deadline:**
- Problem: Stuck HTTP calls hold worker threads indefinitely and keep the process alive.
- Files: `backend/app/market/massive_client.py:43-49`, `massive_client.py:326-337` (`_call`)
- Cause: The Massive SDK stores timeouts but does not pass them to urllib3 (review finding 6).
- Improvement path: Set `client.client.connection_pool_kw["timeout"]` in `make_client`, add a test with a silent socket.

**SSE connections hold the server open:**
- Problem: Each browser tab keeps a streaming response; uvicorn waits for it at shutdown.
- Files: `backend/app/market/stream.py` (`_generate_events`, loops until disconnect)
- Cause: No server-side shutdown signal to streaming generators.
- Improvement path: Pass `--timeout-graceful-shutdown` (3 s documented) in the start command and Dockerfile; consider an app-level shutdown event that ends generators.

**Full-table SSE payload:**
- Problem: Every event re-sends all tickers, so payload grows linearly with watchlist size.
- Files: `backend/app/market/stream.py`
- Improvement path: Acceptable at 10 to 50 tickers (review measured sub-0.1 ms per simulator step). Revisit if the watchlist grows.

## Fragile Areas

**Massive client state machine:**
- Files: `backend/app/market/massive_client.py` (mode, `_requested`, `_fallback`, `_interval`, `_eod_prev`, `_wakeup`)
- Why fragile: Mode switches, fallbacks and backoff interact through shared mutable fields. Several review findings (9, 10, 13) are direct consequences.
- Safe modification: Change one transition at a time and add a regression test per transition. Check `stop()` resets `_fallback` before restart.
- Test coverage: Gaps for empty ticker list, second EOD call failure, EOD rollover, forced-mode poll behaviour (review section 4).

**Global-ish shared cache with sticky baseline:**
- Files: `backend/app/market/cache.py:40-41`
- Why fragile: `prev_close` is kept when omitted; there is no API to clear it, so a stale baseline persists after a source change.
- Safe modification: Always pass `prev_close` explicitly on source-level publishes; add a `clear_prev_close` method before relying on it.

**Simulator prices reset on restart:**
- Files: `backend/app/market/simulator.py`, `backend/app/market/seed_prices.py`
- Why fragile: Persisted positions will show an unexplained P&L jump after restart or re-add (review section 4).
- Safe modification: Persist the baseline with positions before building portfolio P&L.

**Caller contract on symbols:**
- Files: `backend/app/market/cache.py` (no normalisation), `backend/app/market/tracking.py`
- Why fragile: Routes must call `normalize_ticker()` before `get_price()`; forgetting it returns `None` silently.
- Safe modification: Route all lookups through a single helper.

## Scaling Limits

**Massive free-tier rate limits:**
- Current capacity: Poll interval 15 s default (`MASSIVE_POLL_INTERVAL`); one validate call per add spaced by `_validate_gap`.
- Limit: 429 responses double the interval up to `MAX_BACKOFF`; adds bypass backoff today (finding 10).
- Scaling path: Batch snapshot calls (already `get_snapshot_all`); fix finding 10 before increasing watchlist size.

**Single-process in-memory state:**
- Current capacity: One uvicorn worker assumed; `PriceCache` and sources are process-local.
- Limit: Multiple workers would each run their own poller and simulator.
- Scaling path: Run a single worker; move to a shared store only if horizontal scaling is needed.

## Dependencies at Risk

**`massive` SDK pinned below 3:**
- Risk: Finding 6 depends on an SDK internal (`connection_pool_kw`); a major SDK change will break the fix silently.
- Impact: Timeouts stop working and threads leak again.
- Migration plan: Keep the `massive<3` pin in `backend/pyproject.toml` and a test that asserts the timeout reaches urllib3.

**Python version:**
- `backend/pyproject.toml` and `backend/uv.lock` are present; the review ran on Python 3.12 and 3.13. Keep the lock file current with `uv lock --check`.

## Missing Critical Features

**No application entry point, database or frontend:**
- Problem: No `main.py`, no persistence, no portfolio/trade APIs, no `frontend/` build, no Dockerfile.
- Blocks: End-to-end use, the uvicorn shutdown fix (finding 2), and the "prices keep moving" decision (finding 4), which must be made before portfolio P&L is built.

**No live Massive smoke test:**
- Problem: The design calls for a live smoke script (`MARKET_DATA_DESIGN.md` section 12.1) that was never added.
- Blocks: Confidence in the real Massive path.

## Test Coverage Gaps

**Massive path tested only against a fake client:**
- What's not tested: Real response shapes, empty ticker list, failing second EOD call, EOD rollover, forced-mode poll behaviour, thread-abandon on hang.
- Files: `backend/tests/market/test_massive_source.py`, `backend/tests/market/test_massive_parse.py`
- Risk: Finding 1 (wrong URL) passed a fake client for the same reason. Other integration bugs can hide the same way.
- Priority: High

**No HTTP test of the SSE route beyond the basics:**
- What's not tested: Behaviour under disconnect storms and shutdown with active clients.
- Files: `backend/tests/market/test_stream_http.py`, `backend/app/market/stream.py`
- Risk: Shutdown hang in production (review finding 2).
- Priority: Medium

**Weak assertions:**
- What's not tested: `test_rate_limit_doubles_interval_then_recovers` passes without backoff; `test_exception_resilience` injects no exception; `test_custom_event_probability` asserts nothing.
- Files: `backend/tests/market/test_massive_source.py`, `backend/tests/market/test_simulator.py`
- Risk: False confidence in backoff and resilience.
- Priority: Medium

**Fixed sleeps in async tests:**
- Files: Several under `backend/tests/market/`
- Risk: Flaky on slow CI runners.
- Priority: Low

---

*Concerns audit: 2026-11-27*
