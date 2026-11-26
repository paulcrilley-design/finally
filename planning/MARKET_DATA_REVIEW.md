# Market Data Backend: Code Review

**Date:** 2026-11-26
**Commit reviewed:** `40164bc` (main)
**Scope:** `backend/app/market/` (11 modules), `backend/tests/market/` (10 test files), `market_data_demo.py`, `pyproject.toml`, and the documents in `planning/`
**Supersedes:** `planning/archive/MARKET_DATA_REVIEW.md`

---

## 0. Follow-up status (2026-11-26, branch `market-data-review-fixes`)

Sections 1 to 6 describe the code **as reviewed** at `40164bc`; line numbers and results there refer to that commit. This section records what changed afterwards.

**Scope agreed:** keep the simulator fallback, since no Massive key is available yet; fix everything except the Massive issues.

**Update:** finding 1 was fixed afterwards on the same branch, with a test of the real request URLs. 137 tests now pass.

**Result of the first round:** 136 tests pass (also on Python 3.12, with 20 sequential and 8 concurrent runs, and with `-W error`), coverage 94%, `ruff check` and `ruff format --check` clean, README setup commands verified in a clean copy, demo runs.

**The simulator-only backend is ready. The Massive path still has open defects and is untested against the live service: leave `MASSIVE_API_KEY` empty.**

| Finding | Status |
|---|---|
| 1. Wrong snapshot URL | **Fixed**: both calls pass `SnapshotMarketType.STOCKS.value`; `test_snapshot_requests_use_the_real_sdk_urls` stubs only the HTTP layer |
| 2. SSE blocks shutdown | **Handled**: required `--timeout-graceful-shutdown` recorded in `PLAN.md`, the design and developer guide, and tested over real uvicorn. The flag still has to be added when `main.py`, the Dockerfile and scripts are written |
| 3. Empty list skips the probe | **Open** (Massive) |
| 4. Runtime fallback | **Decided**: keep moving in a simulator. Design updated to match. Code unchanged, so it still starts from seed prices and prices jump at the switch (**open**, Massive) |
| 5. Negative `SIM_SEED` | **Fixed** |
| 6 to 10 | **Open** (Massive) |
| 11. `start()` accepts invalid symbols | **Fixed** for both sources with a shared `clean_tickers` (a one-line change in the Massive client) |
| 12. Re-sent tickers | **Documented**: flash only when `timestamp` changes. Applies to the frontend when built |
| 13. Configuration edge cases | **Open** (Massive) |
| 14. Demo colours | **Fixed**: openUI teal and orange |
| 15. Formatting | **Fixed** |

| Test quality item (section 4) | Status |
|---|---|
| Tests that asserted nothing or injected no error | **Fixed** (the two simulator source tests; also the interval test) |
| Fixed sleeps | **Fixed** where a test waits for simulator ticks. Massive tests unchanged |
| No HTTP test of the SSE route | **Fixed**: `test_stream_http.py` |
| Permissive Massive mock | **Partly fixed**: request URLs are now tested through the real SDK; other tests still use the fake client |
| Weak backoff assertion, missing Massive cases | **Open** (Massive) |

| Documentation item (section 5) | Status |
|---|---|
| Both READMEs, summary, `PLAN.md` section 13 | **Fixed** |
| `TEST_PLAN.md` description | **Fixed** in the root README; the template itself is left for later |
| Design listings out of date | **Fixed**: source listings synced, test listings replaced with a file table, known defects listed in section 14.1 |
| Superseded drafts | **Archived** as `archive/MARKET_INTERFACE_V2.md` and `archive/MARKET_SIMULATOR_V2.md` |
| Finding 1 call in the design and `MASSIVE_API.md` examples | **Fixed** |

The notes for downstream work in section 4 are now in `backend/CLAUDE.md`, except the price reset on restart, which remains a design open item.

**Before using a Massive key:** fix findings 3, 4 (seeding) and 6 to 10, then run a live smoke test.

---

## 1. Verdict

**The simulator path is in good shape. The Massive (real data) path does not work and must be fixed before anyone relies on it.**

All 125 tests pass, but the snapshot client builds the wrong URL (finding 1). The tests use a fake client that ignores the argument at fault, so they cannot see it.

| Priority | Findings |
|---|---|
| Critical | 1: wrong snapshot URL |
| High | 2: SSE blocks shutdown. 3: empty watchlist disables key detection. 4: runtime fallback replaces real prices with simulated ones |
| Medium | 5 to 10 |
| Low | 11 to 15 |

Fix 1 to 3 and decide 4 before building the portfolio and trade APIs on this layer. Finding 2 can be fixed when the app entry point and Dockerfile are written.

---

## 2. Test results

Environment: Linux, Python 3.13.17, `massive` 2.2.0, FastAPI 0.128.7, Starlette 0.52.1, uvicorn 0.40.0, urllib3 2.6.3, numpy 2.4.2.

| Check | Result |
|---|---|
| `uv run --extra dev pytest -v` | **125 passed**, 0 failed, 0 skipped (about 6 to 8 s) |
| Same suite, 20 sequential runs | 125 passed every time |
| Same suite, 8 concurrent runs (8 cores) | 125 passed every time |
| `pytest -W error` | 125 passed |
| `ruff check .` | Clean |
| `ruff format --check .` | **4 test files would be reformatted**: `test_models.py`, `test_review_fixes.py`, `test_simulator.py`, `test_simulator_source.py` |
| `uv lock --check` | Lock file up to date |
| `market_data_demo.py` (full 60 s) | Exit 0, summary table printed |
| SSE through real uvicorn | 200, correct headers, `retry:` then `data:` events about every 500 ms |

### Coverage (statements and branches): 93%

| Module | Coverage | Main gaps |
|---|---|---|
| `__init__.py`, `cache.py`, `models.py`, `massive_parse.py`, `seed_prices.py`, `tracking.py` | 100% | |
| `simulator.py` | 94% | Cholesky failure path, loop exception handler |
| `interface.py` | 93% | Base-class defaults for `mode` and `validate_ticker` |
| `factory.py` | 91% | Non-numeric environment values |
| `stream.py` | 91% | The HTTP route itself, cancellation |
| `massive_client.py` | 87% | Fallback delegation, loop error branches, end-of-day edge cases, call spacing |

### What was not tested

No live Massive API key was used. Massive behaviour was checked by reading the installed SDK and by running the real `RESTClient` and `MassiveDataSource` against a local fake HTTP server, or with a stubbed transport. Anything that depends on how the real service responds is marked **conditional** below.

---

## 3. Findings

Each finding marked **reproduced** was triggered by a throwaway script, not only inferred from reading the code.

### Critical

#### 1. Snapshot requests go to a URL that does not exist (reproduced)

`massive_client.py:200` and `:253` pass the enum `SnapshotMarketType.STOCKS`. The SDK compares it with the string `"stocks"` and interpolates it straight into the path. `SnapshotMarketType` is a plain `Enum`, so both go wrong:

```
passed the enum:    /v2/snapshot/locale/global/markets/SnapshotMarketType.STOCKS/tickers
passed .value:      /v2/snapshot/locale/us/markets/stocks/tickers
```

Confirmed on Python 3.12 and 3.13 with `massive` 2.2.0.

Impact, for every Massive key:

- Snapshot mode can never receive a price.
- `validate_ticker` uses the same path, so no ticker can be validated.
- **Conditional:** if the service answers 404, the error is classified `NOT_FOUND` or `OTHER`. A free key then never gets the 403 that switches to end-of-day mode, a bad key may never trigger the simulator fallback, and `validate_ticker` returns `False` for every symbol. The cache stays empty and the UI shows no prices.
- Only `MASSIVE_MODE=eod` avoids the broken path.

**Fix:** pass `SnapshotMarketType.STOCKS.value` (or `"stocks"`) in both places. Add a test that runs the real `RESTClient` with a stubbed `client.client.request` and asserts the exact URL. `FakeClient` accepts any `market_type`, which is why this passed. The same call appears in `MARKET_DATA_DESIGN.md` and `MASSIVE_API.md` section 6.1, so correct those too.

This is the second time a mock has hidden a Massive integration bug (the first was `last_trade.timestamp`). Run the live smoke script proposed in the design (section 12.1) once a key is available. It was never added to the repository.

### High

#### 2. An open SSE connection blocks server shutdown (reproduced)

`_generate_events` loops until the client disconnects. uvicorn waits for open responses to finish before running lifespan shutdown. With one `EventSource` client connected, the server was **still running 8 s after SIGTERM**, and lifespan shutdown (`source.stop()`) never ran. With `--timeout-graceful-shutdown 2` it exited in 2.2 s and shut down cleanly.

Impact: every browser tab holds this connection, so `docker stop` would end in SIGKILL, and any later shutdown work (database close, final snapshot) would be skipped.

**Fix:** set `--timeout-graceful-shutdown` in the Docker `CMD` and start script, and record it in the design. Add this to the app wiring checklist.

#### 3. With no tickers, the startup probe never runs (reproduced)

`_poll_snapshot` returns early when the ticker list is empty (`massive_client.py:251`), and `start()` treats that as success: `last_success` is set although no call was made.

- **Free key:** mode stays `massive-snapshot`. `validate_ticker` gets 403 and raises `MarketDataError`. The poll loop never calls the API, so it never switches to end-of-day mode. The user **can never add a ticker**.
- **Bad key:** no fallback to the simulator, `degraded` stays `false`, and every add fails.

This happens when a user empties the watchlist, holds no positions, and restarts.

**Fix:** probe with a fixed symbol (for example `AAPL`) when the list is empty. Writes are already filtered to tracked tickers. Also handle `FORBIDDEN` and `AUTH` inside `validate_ticker`.

#### 4. A runtime auth failure silently changes real prices into simulated ones (reproduced)

`_fall_back` (`massive_client.py:353`) starts a simulator on the same cache. It starts from the hard-coded seed prices, not the last real prices:

| Ticker | Last real price | Price after fallback |
|---|---|---|
| AAPL | 260.00 (previous close 255.00) | about 190 |
| ZZQX (unknown symbol) | 12.00 | about 216 |

Portfolio value jumps, and trades would execute at invented prices. The daily-change baseline is replaced too. The design says the opposite in section 7.4 ("401 while running: loop stops, `degraded: true`, stale prices stay") and states "Nothing ever invents a price". `SIM_SEED` is also not passed to this simulator.

**Fix (decision needed):** the simplest option is to follow the design: stop polling, keep stale prices, report `degraded`. If prices must keep moving, seed the simulator from the cached prices and previous closes, show the simulated mode clearly in the UI, and update the design.

### Medium

#### 5. A negative `SIM_SEED` crashes startup (reproduced)

`_env_seed` returns `-7`, then `numpy.random.default_rng(-7)` raises `ValueError: expected non-negative integer`. `test_env_seed_never_raises` asserts that `"-7"` parses, but never builds a simulator with it.

**Fix:** reject negative values with a warning, and extend the test to start a source.

#### 6. The request deadline abandons threads, so the process cannot exit (reproduced)

Against a socket that accepts and never answers, `start()` returned after 6 s and `stop()` succeeded, but the **process was still alive 40 s later** and had to be killed. The worker thread stays blocked on the socket, and Python waits for it at exit. Repeated hangs also use up the shared default thread pool.

The SDK stores `self.timeout` but never gives it to urllib3. Setting it on the pool works: with `client.client.connection_pool_kw["timeout"] = client.timeout` the same call failed after 1.0 s.

**Fix:** apply that in `make_client`, keeping `wait_for` as a backstop. This relies on an SDK internal, so cover it with a test and keep the `massive<3` pin.

#### 7. End-of-day mode gives up if the newest weekday returns 403 (reproduced; trigger is conditional)

In `_refresh_eod`, any error on the first date is raised at once (`massive_client.py:281-283`). If the newest session is refused while older ones are allowed, every retry asks for the same date, and no price is published (8 calls, 1 distinct date, empty cache). `MASSIVE_API.md` section 3 notes of 403 that "retrying an older date often works", for example before a session's data is released.

**Fix:** on `FORBIDDEN` for the newest date, continue to the previous one (bounded by the existing 10-day loop).

#### 8. End-of-day refresh publishes the wrong daily baseline (reproduced)

The latest closes are published before the prior session is loaded, using the old `_eod_prev`. With sessions at 100, 110, then 120:

- At rollover the first write is price 120 with previous close **100**. It stays wrong for at least the 12.5 s call gap.
- If the prior-session call then fails, `_eod_prev` becomes empty, but the cache keeps the old value because `prev_close` is sticky. A price of 130 showed a baseline of **110** instead of 120 or none.

**Fix:** publish early only on the first load. On later refreshes, publish once both calls finish, or carry the old latest closes forward as the new baseline. Give the cache a way to clear `prev_close`.

#### 9. `MASSIVE_MODE=snapshot` still switches to end-of-day mode (reproduced)

`start()` respects the forced mode, but `_run` (`massive_client.py:226`) does not check `self._requested`. One poll later the mode changed to `massive-eod`. `test_forced_snapshot_mode_does_not_fall_back` checks only straight after `start()`, before the first loop poll.

**Fix:** add `and self._requested == "auto"` to that branch and let the test wait for a poll.

#### 10. Adding a ticker bypasses rate-limit backoff (reproduced)

`add_ticker` wakes the poller whatever the current interval. With backoff at 120 s, three adds produced three extra calls in 3.6 s. This prolongs the 429 condition.

**Fix:** ignore the wake-up while `_interval > _base_interval`, or enforce a minimum gap between polls.

### Low

11. **`start()` does not validate symbols** (reproduced). `start(["", "bad symbol!", "AAPL"])` tracks and prices all three, while `add_ticker` and `reconcile_tickers` reject the first two. Filter in `start()` for both sources, and test it in the contract tests.
12. **Unchanged tickers are re-sent with their old direction.** Any version change (one add or removal) re-sends every ticker. The frontend could flash the same move twice. Have it flash only when a ticker's `timestamp` changes, and note this in the SSE contract.
13. **Configuration edge cases** (reproduced). `MASSIVE_POLL_INTERVAL=nan` is accepted as the interval. A mistyped `MASSIVE_MODE` raises `ValueError` and stops startup, unlike other bad values, which warn and use a default. `stop()` also leaves `_fallback` set, so a restarted source keeps delegating to a stopped simulator.
14. **Demo colours.** `market_data_demo.py` uses red and green for direction. `PLAN.md` section 2 and the openUI rules say never to. It is a developer tool, so either align it or state that it is exempt.
15. **Formatting.** Run `uv run --extra dev ruff format .`.

---

## 4. Design and code quality

### Done well

- Clear separation: pure maths (`GBMSimulator`), pure parsing (`massive_parse.py`), I/O adapters, cache and transport. The pure parts are fully covered.
- Consumers depend only on `PriceCache`, so they do not need to know the source.
- `reconcile_tickers` is a simple, idempotent answer to the watchlist and positions union.
- The simulator owns its random generators, seeds the cache before `start()` returns, and gives unknown symbols a stable starting price.
- `PriceUpdate` is immutable, and an unknown daily baseline is `None` rather than a misleading 0%.
- `remove()` bumps the version, and a poll in flight cannot bring a removed ticker back.
- The API key goes in a header and is not written to logs.

### Notes for downstream work

- `PriceCache` does not normalise tickers. Routes must call `normalize_ticker` before `get_price`.
- Nothing loads `.env`. The factory reads `os.environ`, so the app or Docker must provide the variables.
- Simulator prices reset on restart, and removing then re-adding a ticker resets it to its starting price. Persisted positions will show a P&L jump. The design lists persisting the baseline as an open item.
- At 2 decimal places many simulator ticks are flat (measured from 5% for NVDA to 37% for JPM). This is expected.
- Simulator cost is small: with 50 tickers, a step takes under 0.1 ms and an add under 1 ms.

### Test quality

- **Mocks are too permissive** (finding 1). Prefer stubbing the HTTP layer under the real SDK.
- `test_rate_limit_doubles_interval_then_recovers` asserts `interval > 0.05 or last_error is None`, which also passes when no backoff happens.
- `test_exception_resilience` injects no exception. `test_custom_event_probability` asserts nothing.
- Several async tests rely on fixed sleeps. They were stable here but could be flaky on a slow CI runner.
- No test calls `GET /api/stream/prices` over HTTP.
- No test covers an empty ticker list with Massive, a failing second end-of-day call, or the end-of-day rollover.

---

## 5. Documentation

| Document | Problem |
|---|---|
| Root `README.md` | `uv sync` then `uv run pytest` **fails** in a clean copy (`Failed to spawn: pytest`), and the demo cannot import `rich`. Both are in the `dev` extra. Use `uv sync --extra dev` (reproduced) |
| `backend/README.md` | `uv sync --dev` also fails to install pytest (reproduced). The module list omits `massive_parse.py` and `tracking.py` |
| `MARKET_DATA_SUMMARY.md` | Out of date: says 73 tests, 6 test modules, 8 modules, 84% coverage and a `test_massive.py` that no longer exists. Actual: 125, 10, 11 and 93%. It omits end-of-day mode, fallback and `tracking.py`. "All issues resolved" is no longer accurate |
| `MARKET_DATA_DESIGN.md` | Code listings differ from the repository (runtime fallback, validation spacing, end-of-day publishing, unknown-ticker pricing). Contains the finding 1 call and calls the Massive attribute names verified without any request-path check |
| `MARKET_INTERFACE.md`, `MARKET_SIMULATOR.md` | Still describe "proposed" changes that are built or dropped (`get_prev_closes`, random unknown-ticker prices). The design's checklist (step 7) says to archive superseded drafts |
| `PLAN.md` section 13 | Questions 2 to 4 are answered by the design but still listed as open |
| `TEST_PLAN.md` | Still a template, although the root README calls it the testing strategy |

---

## 6. Recommended order of work

1. Fix the snapshot URL and add a URL-level test (finding 1).
2. Fix the empty-list probe and decide the runtime fallback behaviour (findings 3 and 4).
3. Fix findings 5 to 10, each with a regression test.
4. Run a live smoke test with a real key, including a free key if possible.
5. Add the graceful shutdown timeout when `main.py` and the Dockerfile are written (finding 2).
6. Tidy the low-priority items and update the READMEs and summary.
