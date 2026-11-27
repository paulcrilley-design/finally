---
last_mapped_commit: 7dc6485eb92dc2d388eefd949c257a428bdb494f
last_mapped_at: 2026-11-27
---
# Coding Conventions

**Analysis Date:** 2026-11-27

## Scope of the Current Codebase

Only the backend market data subsystem is implemented. Everything else is planned in `planning/PLAN.md`:

- Implemented: `backend/app/market/` (Python 3.12, FastAPI-compatible, async), with tests in `backend/tests/market/`.
- Not yet present: `frontend/` is empty (the design foundation under `frontend/src/` referenced in `CLAUDE.md` does not exist in the repo yet). No TypeScript, React or Tailwind conventions can be observed yet. For UI work, follow `planning/OUI_FORMAT.md`.
- `test/` holds only Playwright tooling in `node_modules` and a `test-results/.last-run.json`; no E2E specs are committed.
- Lint/format config is in `backend/pyproject.toml` (`[tool.ruff]`).

## Naming Patterns

**Files:**
- Python modules are `snake_case.py`, named by role: `cache.py`, `models.py`, `interface.py`, `factory.py`, `simulator.py`, `massive_client.py`, `massive_parse.py`, `stream.py`, `tracking.py`, `seed_prices.py` (all in `backend/app/market/`).
- Test files are `test_<module>.py` (e.g. `backend/tests/market/test_cache.py`, `test_massive_source.py`). Shared test helpers live in `backend/tests/market/helpers.py`; they are imported with a relative import: `from .helpers import wait_until`.
- Each package has an `__init__.py` that declares a public API via `__all__` (see `backend/app/market/__init__.py`).

**Functions:**
- `snake_case`. Public: `create_market_data_source`, `start_market_data`, `reconcile_tickers`, `normalize_ticker`, `clean_tickers`.
- Module-private helpers are prefixed with a single underscore: `_env_float`, `_env_seed` (`backend/app/market/factory.py`), `_generate_events` (`backend/app/market/stream.py`), `_write`, `_run_loop` (`backend/app/market/simulator.py`).
- Async I/O entry points are `async def` (e.g. `start`, `stop`, `add_ticker`, `remove_ticker` on `MarketDataSource` in `backend/app/market/interface.py`). Pure computation stays synchronous (e.g. `GBMSimulator.step` in `backend/app/market/simulator.py`).
- Boolean-returning helpers use `is_`/`validate_` prefixes: `is_valid_symbol`, `validate_ticker`.

**Variables:**
- `snake_case`. Module-level constants are `UPPER_SNAKE_CASE`: `MAX_BACKOFF`, `FREE_TIER_CALL_GAP`, `HEARTBEAT_SECONDS`, `_TICKER_RE`, `NEW_YORK`.
- Loggers are always `logger = logging.getLogger(__name__)` at module top.
- Instance attributes that are internal use a leading underscore (`self._prices`, `self._lock`, `self._version` in `backend/app/market/cache.py`).

**Types / Classes:**
- `PascalCase` classes. Abstract base: `MarketDataSource(ABC)`. Implementations are named `<Thing><Role>`: `SimulatorDataSource`, `MassiveDataSource`, `GBMSimulator`, `PriceCache`, `PriceUpdate`.
- Exceptions end in `Error`: `MarketDataError`, `MarketDataUnavailableError`, `MassiveCallError`.
- Enumerations use `enum` classes (`ErrorKind` in `backend/app/market/massive_parse.py`).

## Code Style

**Formatting:**
- Tool: Ruff formatter (implied by the Ruff config; no separate Black config).
- Line length: 100 (`[tool.ruff] line-length = 100` in `backend/pyproject.toml`). E501 is ignored for lint because the formatter handles wrapping.
- Quotes: double quotes; trailing commas in multi-line calls and literals.
- Use parenthesised multi-line signatures for functions with several parameters (see `PriceCache.update` in `backend/app/market/cache.py`).

**Linting:**
- Tool: Ruff (`uv run --extra dev ruff check .` from `backend/`).
- Selected rule sets: `E`, `F`, `I` (isort), `N` (pep8-naming), `W`. `E501` ignored.
- Known exceptions in use: `# noqa: E731` for a lambda assigned to a name in `backend/tests/market/test_design_extras.py`.

**Type hints:**
- Every module that uses forward references starts with `from __future__ import annotations` (e.g. `backend/app/market/models.py`, `cache.py`, `interface.py`, `factory.py`, `simulator.py`, `massive_client.py`, `stream.py`).
- Modern union syntax is used: `float | None`, `dict[str, PriceUpdate]`, `list[str]`. Do not use `Optional[...]` or `typing.List`.
- Abstract methods declare full signatures; `Any` is used sparingly (`status() -> dict[str, Any]`).

## Import Organization

**Order (enforced by Ruff `I`):**
1. Standard library (`asyncio`, `logging`, `dataclasses`, `zoneinfo`, ...)
2. Third-party (`fastapi`, `numpy`, `massive`)
3. First-party, using relative imports inside the `app.market` package (`from .cache import PriceCache`, `from .interface import ...`)

Tests use absolute imports for the package under test (`from app.market.cache import PriceCache`) and relative imports only for helpers in the same test package (`from .helpers import wait_until`, `from .test_massive_source import FakeClient`).

**Path Aliases:**
- None. Imports are package-absolute (`app.*`, `tests.*`) because the backend is run from `backend/`.

## Data Modelling

- Value objects are frozen, slotted dataclasses: `@dataclass(frozen=True, slots=True)` on `PriceUpdate` (`backend/app/market/models.py`). Derived values are `@property`, not stored fields.
- Serialisation for JSON/SSE goes through an explicit `to_dict()` method, never `asdict()`, so the wire format is controlled.
- Prices are rounded to 2 dp at the cache boundary (`PriceCache.update`); internal simulator math is unrounded.

## Error Handling

**Pattern: typed exceptions and explicit `None`, not sentinel values.**
- Source-level failures raise `MarketDataError` (or subclass `MarketDataUnavailableError` for "can never work with this config"), defined in `backend/app/market/interface.py`.
- Lookups return `None` for "unknown" and callers must check it. `PriceCache.get` and `get_price` return `None`; `PriceUpdate.day_change` returns `None` when the baseline is missing (never `0`). The rule from `backend/CLAUDE.md`: a `None` price means unknown, so reject the trade rather than substituting a value.
- Environment parsing never raises. Invalid values log a warning and fall back to a default: see `_env_float` and `_env_seed` in `backend/app/market/factory.py`.
- Background loops swallow exceptions so they keep running, but log them with `logger.exception`:
  ```python
  try:
      for ticker, price in self._sim.step().items():
          self._write(ticker, price)
  except Exception:
      logger.exception("Simulator step failed")
  await asyncio.sleep(self._interval)
  ```
  (`backend/app/market/simulator.py`; the Massive loop does the same at `backend/app/market/massive_client.py`.)
- Cancellation is always re-raised after cleanup: `except asyncio.CancelledError: logger.info(...); raise` (`backend/app/market/stream.py`).
- Input validation at boundaries: `normalize_ticker()` and `clean_tickers()` / `is_valid_symbol()` run before data enters the system (`backend/app/market/interface.py`). Invalid symbols are dropped with a warning, not raised.
- Raise `ValueError` for programmer errors on constructor arguments (e.g. `bad MASSIVE_MODE` in `MassiveDataSource.__init__`).
- Keep the broad `except Exception` to background loops and the top-level call wrapper; elsewhere catch specific exceptions (`AuthError`, `BadResponse` from `massive.exceptions`).

## Logging

**Framework:** standard library `logging`, one logger per module.

**Patterns:**
- Use `%`-style lazy arguments, never f-strings: `logger.info("Simulator: added ticker %s", ticker)`, `logger.warning("Ignoring invalid ticker symbol %r", ticker)`.
- Levels: `info` for lifecycle events (source chosen, ticker added or removed, SSE client connected), `warning` for ignored input, `error` for fallbacks (`start_market_data` in `backend/app/market/factory.py`), `exception` inside `except` blocks in loops.
- Warn once per condition where it would otherwise repeat every tick: `_warned_invalid` set in `backend/app/market/tracking.py`; `_eod_day` in `MassiveDataSource`.
- `print()` is not used in the library code. The terminal demo `backend/market_data_demo.py` uses `rich` for output.

## Comments and Docstrings

**Docstrings:**
- Every module starts with a one-line docstring (`"""Thread-safe in-memory price cache."""`).
- Every public class and function has a docstring. Imperative or descriptive summary, then detail where behaviour is non-obvious (e.g. `PriceCache.update` documents that `prev_close` is sticky).
- Docstrings describe contracts and invariants ("Call exactly once.", "Safe to call repeatedly.", "No-op if absent."). Keep them to that style.
- Public `__init__.py` modules document the public API in the module docstring as an indented list (`backend/app/market/__init__.py`).
- Not JSDoc/TSDoc style; no type info is repeated in docstrings because hints are present.

**Inline comments:**
- Used to explain *why*, especially for external-service quirks: `# retries=0: the SDK's default of 3 retries includes HTTP 429...` (`make_client`, `backend/app/market/massive_client.py`), `# 5 requests/minute => at most one call per 12 s`.
- Section banners inside classes use `# --- Public API ---` and `# --- MarketDataSource ---`.
- Review-driven fixes are referenced in tests, not in source (`tests/market/test_review_fixes.py`). Do not add comments that narrate history.

## Function Design

- Keep functions small; long logic is split into `_private` helpers (e.g. `_add_ticker_internal`, `_rebuild_cholesky` in the simulator).
- Parameters: keyword defaults for tunables (`poll_interval: float = 15.0`, `update_interval`, `seed: int | None = None`), so tests can inject small values. Pass dependencies in the constructor (`price_cache`, `client: Any = None  # injectable for tests`).
- Return values: return the created object where useful (`PriceCache.update` returns the `PriceUpdate`); return `None` for commands.
- Prefer returning new immutable objects over mutating shared state; the cache is the single mutable store and it is protected by a lock.

## Concurrency

- Thread-safe shared state uses `threading.Lock` with `with self._lock:` around every read and write (`backend/app/market/cache.py`). Every public method of `PriceCache` takes the lock, including read-only ones such as `version`, `__len__`.
- Async code uses `asyncio.Lock` for serialising calls (`self._validate_lock` in `MassiveDataSource`) and `asyncio.Event` for wakeups.
- Sleeps in loops use `await asyncio.sleep(...)`; never `time.sleep` inside async code.

## Module Design

**Exports:**
- Each package exports its public surface through `__init__.py` with an explicit `__all__` list. Consumers import from the package (`from app.market import PriceCache, create_stream_router`), not from internal modules. Internal names with a leading underscore (e.g. `_generate_events`) may be imported only by tests.

**Barrel files:**
- `backend/app/market/__init__.py` is the only barrel. Do not add barrels to `tests/`.

**Abstract interfaces:**
- New data providers subclass `MarketDataSource` (`backend/app/market/interface.py`) and implement `start`, `stop`, `add_ticker`, `remove_ticker`, `get_tickers`. Optional capabilities (`mode`, `validate_ticker`, `status`) have default implementations.

## Frontend Conventions (for when `frontend/` is built)

- Not yet observable in this repo. Follow `planning/OUI_FORMAT.md` for colours, fonts, logo and components.
- `CLAUDE.md` requires the existing design foundation under `frontend/src/` to be preserved and reused; do not replace it when adding UI.
- `planning/PLAN.md` specifies Next.js, TypeScript, Tailwind v4 and Recharts. Treat these as the intended stack until the files exist.

---

*Convention analysis: 2026-11-27*
