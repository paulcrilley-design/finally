---
last_mapped_commit: 7dc6485eb92dc2d388eefd949c257a428bdb494f
last_mapped_at: 2026-11-27
---
# Testing Patterns

**Analysis Date:** 2026-11-27

## Scope

Only the backend market data subsystem has tests. Test locations:

- `backend/tests/market/` — unit, integration, contract, HTTP and regression tests for `backend/app/market/`.
- `test/` — reserved for Playwright E2E tests (planned, see `planning/PLAN.md` "E2E Tests"). Only `node_modules/` and `test-results/.last-run.json` exist today; no specs are committed.
- `frontend/` — no tests yet. `planning/PLAN.md` leaves the frontend runner (Jest or Vitest) undecided.

## Test Framework

**Runner:**
- pytest `>=8.3.0` (declared in `backend/pyproject.toml` under `[project.optional-dependencies] dev`).
- Config: `[tool.pytest.ini_options]` in `backend/pyproject.toml`:
  - `testpaths = ["tests"]`, `python_files = ["test_*.py"]`, `python_classes = ["Test*"]`, `python_functions = ["test_*"]`
  - `asyncio_mode = "auto"` — every `async def test_*` runs under asyncio without a marker.
  - `asyncio_default_fixture_loop_scope = "function"`
- Async plugin: `pytest-asyncio >=0.24.0`.
- Coverage: `pytest-cov >=5.0.0`; `[tool.coverage.run] source = ["app"]`, `omit = ["tests/*"]`; `exclude_lines` includes `pragma: no cover`, `if TYPE_CHECKING:`, `raise NotImplementedError`.

**Assertion library:**
- Plain `assert` statements (pytest rewriting). Use `pytest.raises` for expected exceptions and `pytest.mark.parametrize` for tables of cases.
- HTTP testing uses `httpx` (`httpx.AsyncClient(trust_env=False)`) against a real `uvicorn` server.

**Run Commands (from `backend/`):**
```bash
uv sync --extra dev                              # Install dependencies incl. test tools (once)
uv run --extra dev pytest -v                     # Run all tests
uv run --extra dev pytest tests/market/test_cache.py   # Run one file
uv run --extra dev pytest -k simulator           # Run tests matching a name
uv run --extra dev pytest --cov=app              # Coverage
uv run --extra dev ruff check app/ tests/        # Lint
```
Per the project token rules, run only the tests relevant to the change, not the whole suite, unless asked.

## Test File Organization

**Location:**
- Separate tree: tests live in `backend/tests/`, mirroring the package. Market tests are in `backend/tests/market/`; there is one `__init__.py` per test package so relative helper imports work.

**Naming:**
- Files: `test_<subject>.py`. Current subject names: `test_cache.py`, `test_models.py`, `test_interface.py`, `test_factory.py`, `test_simulator.py` (pure GBM), `test_simulator_source.py` (async source behaviour), `test_massive_parse.py`, `test_massive_source.py`, `test_stream_http.py`, `test_contract.py`, `test_design_extras.py`, `test_review_fixes.py`.
- Test classes: `Test<Subject>` (e.g. `TestPriceCache`, `TestFactory`, `TestSimulatorDataSource`). Test functions: `test_<behaviour>`; use descriptive names (`test_first_update_is_flat`, `test_remove_nonexistent`).
- Regression tests for reviewed defects go in `test_review_fixes.py`, grouped by the review item they cover; new regressions should follow that pattern.

**Structure:**
```
backend/tests/
├── __init__.py
├── conftest.py                 # shared fixtures (currently only event_loop_policy)
└── market/
    ├── __init__.py
    ├── helpers.py              # wait_until(), shared polling helper
    ├── test_cache.py           # PriceCache (sync)
    ├── test_models.py          # PriceUpdate properties and to_dict
    ├── test_simulator.py       # GBMSimulator maths (sync)
    ├── test_simulator_source.py# SimulatorDataSource lifecycle (async)
    ├── test_massive_source.py  # MassiveDataSource with FakeClient
    ├── test_contract.py        # parametrized over simulator and massive
    ├── test_stream_http.py     # real uvicorn + httpx SSE test
    └── ...
```

## Test Structure

**Class-based grouping for a subject, plus module-level functions for standalone checks:**
```python
# backend/tests/market/test_cache.py
from app.market.cache import PriceCache


class TestPriceCache:
    """Unit tests for the PriceCache."""

    def test_direction_up(self):
        """Test price update with upward direction."""
        cache = PriceCache()
        cache.update("AAPL", 190.00)
        update = cache.update("AAPL", 191.00)
        assert update.direction == "up"
        assert update.change == 1.00
```

**Async classes** use the class-level marker (`backend/tests/market/test_simulator_source.py`):
```python
@pytest.mark.asyncio
class TestSimulatorDataSource:
    async def test_start_populates_cache(self):
        cache = PriceCache()
        source = SimulatorDataSource(price_cache=cache, update_interval=0.1)
        await source.start(["AAPL", "GOOGL"])
        assert cache.get("AAPL") is not None
        await source.stop()
```
Note: `test_stream_http.py` and `test_review_fixes.py` rely on `asyncio_mode = "auto"` and carry no marker. Either style works; prefer the explicit marker in new classes that mix sync and async tests.

**Patterns:**
- Every test has a one-line docstring (`"""Test that ..."""`). Keep this for new tests.
- Setup: build fresh objects inside each test (`cache = PriceCache()`). There is no shared mutable state between tests.
- Teardown: call `await source.stop()` at the end of the test. Use `try/finally` when a failure would otherwise leak a running task (see `test_review_fixes.py::test_any_sim_seed_still_starts`). Stopping twice must be safe; a test asserts this (`test_stop_is_clean`).
- Fast timing: start sources with small intervals (`update_interval=0.01`, `poll_interval=0.02`) and wait on conditions, not fixed sleeps.

**Waiting for asynchronous state:**
Use `wait_until` from `backend/tests/market/helpers.py` instead of `asyncio.sleep` for fixed durations:
```python
async def wait_until(condition: Callable[[], bool], timeout: float = 5.0) -> None:
    async with asyncio.timeout(timeout):
        while not condition():
            await asyncio.sleep(0.005)
```
Example: `await wait_until(lambda: cache.version >= initial_version + 3)`.

## Mocking

**Framework:** `unittest.mock` (`patch`, `patch.dict`) and pytest's `monkeypatch`. Both are in use; prefer `monkeypatch` for new tests because it is scoped to the test and restores automatically.

**Environment variables:** always use `monkeypatch.setenv` / `monkeypatch.delenv`, or `patch.dict(os.environ, {...}, clear=True)` for a fully controlled environment (`backend/tests/market/test_factory.py`):
```python
def test_creates_simulator_when_no_api_key(self):
    cache = PriceCache()
    with patch.dict(os.environ, {}, clear=True):
        source = create_market_data_source(cache)
    assert isinstance(source, SimulatorDataSource)
```
```python
@pytest.mark.parametrize("raw", ["-7", "0", "x"])
async def test_any_sim_seed_still_starts(monkeypatch, raw):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.setenv("SIM_SEED", raw)
    ...
```

**Replacing internal methods:**
```python
monkeypatch.setattr(source._sim, "step", flaky_step)   # inject a failure into the loop
monkeypatch.setattr(np.linalg, "cholesky", fail)      # force the degraded path
```

**External API client (Massive SDK):** the real network is never called in tests. Use the injectable `client` argument of `MassiveDataSource` with the `FakeClient` in `backend/tests/market/test_massive_source.py`:
- `FakeClient` mimics `massive.RESTClient` methods (`get_snapshot_all`, `get_snapshot_ticker`, ...) and returns values, raises exceptions, or returns a `Seq` of responses in order.
- Responses are real SDK models, not dicts: `TickerSnapshot.from_dict({...})` and `GroupedDailyAgg(...)` from `massive.rest.models`; errors are real `massive.exceptions` types (`AuthError`, `BadResponse`).
- Helper factories `snap(ticker, price, prev=...)` and `bar(ticker, close)` build fixtures.

**What to Mock:**
- External network clients (Massive REST) — always, via the injected `client`.
- Environment variables — via `monkeypatch` or `patch.dict`.
- Random or failing internals (step functions, linear algebra) when testing error paths.
- Time-dependent behaviour: `PriceCache.update` accepts `timestamp=`; pass explicit timestamps instead of mocking `time.time`.

**What NOT to Mock:**
- `PriceCache` and `PriceUpdate` — these are pure and cheap; use the real objects.
- The `SimulatorDataSource` in its own tests; it has no external dependency. Seed it (`seed=`) when reproducibility matters.
- The HTTP layer for SSE: `test_stream_http.py` runs a real `uvicorn.Server` on an ephemeral port (`port=0`) with an `httpx` client. Keep this style for endpoint tests rather than mocking the response.
- The `massive` SDK models: build them with `from_dict`, so the tests catch SDK shape changes.

## Determinism and Seeds

- The simulator accepts `seed` (`GBMSimulator(..., seed=7)`), using its own `numpy` and `random` generators so global RNG state is untouched. Use fixed seeds for any assertion about a series, e.g. `test_same_seed_same_series` in `backend/tests/market/test_design_extras.py`.
- Statistical checks (volatility calibration) use large sample counts and loose tolerances; document the tolerance in a comment.
- Environment-driven seed input (`SIM_SEED`) must never raise; `_env_seed` is tested with a parametrized table of bad values.

## Fixtures and Factories

**Shared fixtures:**
- `backend/tests/conftest.py` defines `event_loop_policy` (returns `asyncio.DefaultEventLoopPolicy()`). Add new cross-module fixtures here; keep module-specific fixtures in the test file.
- Contract fixtures: `source` in `backend/tests/market/test_contract.py` is parametrized with `params=["simulator", "massive"]` so one set of behavioural tests covers every `MarketDataSource` implementation. Add new providers to `build()` there.

**Test data:**
- Tickers in tests are the seed tickers from `backend/app/market/seed_prices.py` (AAPL, GOOGL, MSFT, ...). Use real-looking prices (`190.00`) so the 2-dp rounding is obvious in assertions.
- Shared helpers are imported from sibling test modules (`from .test_massive_source import FakeClient, Seq, bar, make, snap`). Prefer moving a helper to `helpers.py` if a third module needs it.

**Location:**
- `backend/tests/market/helpers.py` (polling helper), `backend/tests/market/test_massive_source.py` (FakeClient and factories), `backend/tests/conftest.py` (fixtures).

## Coverage

**Requirements:** None enforced. No `fail_under` is set in `backend/pyproject.toml`.

**View Coverage:**
```bash
cd backend && uv run --extra dev pytest --cov=app --cov-report=term-missing
```

## Test Types

**Unit Tests:**
- Pure objects: `PriceCache`, `PriceUpdate`, `GBMSimulator` maths, `normalize_ticker`, `is_valid_symbol`, `classify_error`. Synchronous, no fixtures beyond the object itself.

**Integration Tests:**
- Source lifecycle with a real event loop and real timers: `SimulatorDataSource` start/stop/add/remove (`test_simulator_source.py`), factory fallback to the degraded simulator (`test_design_extras.py`), `reconcile_tickers` against a source.

**Contract Tests:**
- `backend/tests/market/test_contract.py` runs the same behavioural checks against every `MarketDataSource` implementation. New providers must pass these.

**HTTP / Streaming Tests:**
- `backend/tests/market/test_stream_http.py` verifies SSE headers, the `retry:` preamble, the payload shape and graceful shutdown with an open client. Assert on exact header values and event lines.

**Regression Tests:**
- `backend/tests/market/test_review_fixes.py` and `test_design_extras.py` pin down behaviour after review. When fixing a bug, add a test to the matching file with a comment naming the review item.

**E2E Tests:**
- Not yet implemented. Planned: Playwright in `test/` running on the host against the single app container started with `LLM_MOCK=true` (`planning/PLAN.md`). `test/` already contains Playwright `node_modules`, so `@playwright/test` is the expected runner.

## Common Patterns

**Async testing with timeouts:**
```python
async with asyncio.timeout(10):
    async with httpx.AsyncClient(trust_env=False) as client:
        async with client.stream("GET", url) as response:
            ...
```
Wrap any test that opens a network connection or waits on a background task in `asyncio.timeout(...)` so a hang fails fast.

**Error testing:**
```python
def test_classify_error_is_not_fooled_by_substrings():
    assert classify_error(RuntimeError("connect to host:4290 failed")) is ErrorKind.NETWORK
    body = BadResponse('{"error":"see api key docs"}')
    assert classify_error(body) is ErrorKind.OTHER
```
Assert on the specific exception type or returned enum member; do not assert on exception message text unless the message is the contract.

**Logging assertions:**
- Use pytest's `caplog` fixture (`test_simulator_source.py::test_exception_resilience`) to check that background loops log the expected message. Do not assert on log text from info-level lifecycle messages.

**Parametrized tables:**
```python
@pytest.mark.parametrize(
    "raw,expected",
    [("42", 42), ("0", 0), ("-7", None), ("--5", None), ("x", None), ("", None)],
)
def test_env_seed_never_raises(monkeypatch, raw, expected): ...
```

**Known gaps:**
- No tests for `backend/market_data_demo.py`.
- No frontend or E2E tests yet.
- `conftest.py`'s `event_loop_policy` fixture is a legacy pattern; pytest-asyncio 0.24+ manages the loop through `asyncio_mode = "auto"`, so new tests should not depend on it.

---

*Testing analysis: 2026-11-27*
