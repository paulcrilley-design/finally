# Market Data Interface (Unified Python API)

The single Python API the rest of FinAlly uses to get stock prices. It selects the **Massive API** when `MASSIVE_API_KEY` is set and non-empty, and otherwise the **built-in simulator** (see MARKET_SIMULATOR.md). Massive endpoint details are in MASSIVE_API.md.

Code lives in `backend/app/market/`. Most of this is already implemented (`interface.py`, `cache.py`, `models.py`, `factory.py`, `massive_client.py`, `simulator.py`, `stream.py`). Section 7 lists the changes this design requires beyond what exists.

---

## 1. Design principles

1. **Producers write, consumers read.** A data source (simulator or Massive poller) runs in the background and writes to one `PriceCache`. Everything else (SSE, portfolio valuation, trade execution, watchlist) reads only from the cache and never knows which source is active.
2. **One interface, two implementations** (strategy pattern), chosen once at startup by a factory from an environment variable.
3. **Global, not per-user.** One cache, one source. The tickers to track are the union of every user's watchlist and open positions (PLAN.md Section 3).
4. **Never break the stream.** A failed poll logs and retries; stale prices stay in the cache.
5. **Plan-aware.** A Massive key may be free (end-of-day only) or paid (snapshots). The Massive source detects what the key can do and degrades gracefully instead of failing.

## 2. Architecture

```
create_market_data_source(cache)
        │   MASSIVE_API_KEY set?
   ┌────┴─────────────────┐
   no                     yes
   │                      │
SimulatorDataSource   MassiveDataSource
 (GBM, 500 ms)         ├─ mode "snapshot": /v2/snapshot (1 call/poll)   [paid plans]
   │                   └─ mode "eod": /v2/aggs/grouped (1 call/day)     [free plan]
   └──────────┬───────────┘
              ▼
          PriceCache  (thread-safe, versioned)
              │
   ┌──────────┼────────────┬──────────────┐
   ▼          ▼            ▼              ▼
 SSE stream  Portfolio   Trade exec   Watchlist API
```

## 3. Public API

Import everything from the package:

```python
from app.market import (
    PriceCache, PriceUpdate, MarketDataSource,
    create_market_data_source, create_stream_router,
)
```

### 3.1 `PriceUpdate` (immutable, `models.py`)

| Field / property | Meaning |
|---|---|
| `ticker: str` | Upper-case symbol |
| `price: float` | Latest price, rounded to 2 dp |
| `previous_price: float` | Price before this update (equal to `price` on first update) |
| `timestamp: float` | Unix **seconds** |
| `change`, `change_percent` | Versus `previous_price` (tick-to-tick, not daily) |
| `direction` | `"up"`, `"down"` or `"flat"` |
| `to_dict()` | JSON form used by SSE |

Proposed additions (Section 7): `prev_close: float | None` and properties `day_change` / `day_change_percent`, so the watchlist's "daily change %" has a defined baseline (resolves the open question in PLAN.md Section 13, item 4).

### 3.2 `PriceCache` (`cache.py`)

```python
cache.update(ticker, price, timestamp=None) -> PriceUpdate   # producers only
cache.get(ticker)        -> PriceUpdate | None
cache.get_price(ticker)  -> float | None
cache.get_all()          -> dict[str, PriceUpdate]            # shallow copy
cache.remove(ticker)
cache.version            # int, bumps on every update (SSE change detection)
len(cache); ticker in cache
```
Consumers must treat `None` as "no price known" and reject the trade or show a placeholder. They must never invent a price.

### 3.3 `MarketDataSource` (`interface.py`)

```python
class MarketDataSource(ABC):
    async def start(self, tickers: list[str]) -> None   # begin background task; call once
    async def stop(self) -> None                        # idempotent
    async def add_ticker(self, ticker: str) -> None     # no-op if present
    async def remove_ticker(self, ticker: str) -> None  # also evicts from cache
    def get_tickers(self) -> list[str]
```
Proposed additions (default implementations so existing code keeps working):

```python
    async def validate_ticker(self, ticker: str) -> bool        # is this a real, priceable symbol?
    async def get_prev_closes(self, tickers: list[str]) -> dict[str, float]   # daily-change baseline
    @property
    def mode(self) -> str            # "simulator" | "massive-snapshot" | "massive-eod"
```
`mode` is exposed by `GET /api/health` so the UI can show a data-source badge ("Simulated", "15-min delayed", "End of day").

### 3.4 Factory (`factory.py`)

```python
def create_market_data_source(price_cache: PriceCache) -> MarketDataSource:
    key = os.environ.get("MASSIVE_API_KEY", "").strip()
    return MassiveDataSource(api_key=key, price_cache=price_cache) if key \
           else SimulatorDataSource(price_cache=price_cache)
```
Optional env overrides (all have defaults): `MASSIVE_POLL_INTERVAL` (seconds; default 15), `MARKET_FORCE_SIMULATOR=true` (ignore the key, handy for demos and tests).

## 4. Lifecycle and wiring (FastAPI)

Create the cache and source in the app lifespan, not at import time, and keep them on `app.state`:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    cache = PriceCache()
    source = create_market_data_source(cache)
    await source.start(tickers_in_use())      # union of all users' watchlists + positions
    app.state.price_cache, app.state.market = cache, source
    app.include_router(create_stream_router(cache))
    yield
    await source.stop()
```

Rules for callers:
- **Watchlist add:** `await market.add_ticker(t)` after checking `await market.validate_ticker(t)`.
- **Watchlist remove:** call `remove_ticker` only if no user holds a position in it or still watches it; otherwise valuation loses its price.
- **Trades:** read `cache.get_price(ticker)`; reject if `None`.
- **Portfolio total value:** sum from `cache.get_all()`; no direct source access.

## 5. Massive implementation details

### 5.1 Mode detection

On `start()` the source probes once and picks a mode:

1. Call the snapshot endpoint for the tracked tickers.
   - Success → `snapshot` mode; poll every `poll_interval` (default 15 s; 2-5 s on Advanced).
   - HTTP 403 `NOT_AUTHORIZED` → the key lacks snapshots, so fall to `eod`.
2. `eod` mode: call `get_grouped_daily_aggs` for the most recent trading day (step back over weekends/holidays), write each tracked ticker's close to the cache once, and refresh hourly. Log a warning that prices are end-of-day and static.

If neither works (401, no network), log the error, fall back to the simulator for that process, and report `mode="simulator"` plus a `degraded` flag in health. This keeps the app usable with a wrong key instead of showing an empty page. (Alternative: fail fast at startup. We choose graceful fallback because the app's primary job here is demonstration.)

### 5.2 Price extraction (snapshot mode)

Preference order per ticker: `last_trade.price` (Developer+), then `min.close`, then `day.close`, then `prev_day.close`. Skip the ticker (keep the old cache entry) if none exist.

### 5.3 Timestamp normalization

Massive timestamps appear in nanoseconds, milliseconds and seconds. The existing code assumes milliseconds and divides by 1000, which is wrong for nanosecond `lastTrade.t`. Use one helper:

```python
def to_unix_seconds(ts: int | float) -> float:
    if ts > 1e17: return ts / 1e9     # nanoseconds
    if ts > 1e14: return ts / 1e6     # microseconds
    if ts > 1e11: return ts / 1e3     # milliseconds
    return float(ts)                  # seconds
```
Fall back to `time.time()` when the timestamp is missing or implausible.

### 5.4 Errors and rate limiting

| Condition | Behaviour |
|---|---|
| 429 | Double the interval (cap 120 s), restore after a success. Free tier is 5 req/min, so never poll faster than 15 s |
| 401 | Log once at ERROR, stop polling, degrade as in 5.1 |
| 403 | Switch to `eod` mode (if first probe) or log and keep stale data |
| Network/timeout | Log, keep stale data, retry next interval |
| Ticker missing from response | Leave cache entry unchanged; log at debug |

The synchronous `RESTClient` always runs in `asyncio.to_thread`. Set a request timeout so a hung call cannot stall the loop.

### 5.5 `validate_ticker`

Massive: one single-ticker snapshot (paid) or `get_previous_close_agg` (free); invalid ticker means empty or `NOT_FOUND`. Simulator: accept any `^[A-Z]{1,5}$` symbol (unknown ones get a random seed price; see MARKET_SIMULATOR.md).

### 5.6 `get_prev_closes`

Massive: from `prev_day.close` in snapshots, or grouped daily bars in `eod` mode. Simulator: the seed price (the simulator's "previous close" is its start-of-session price). The cache stores it as `prev_close` on each update, giving the watchlist a stable daily baseline.

## 6. SSE contract

Unchanged from the existing `stream.py`: `GET /api/stream/prices`, `retry: 1000`, and an event only when `cache.version` changed, with one object keyed by ticker:

```
data: {"AAPL": {"ticker":"AAPL","price":190.5,"previous_price":190.4,"timestamp":1764081000.2,
                "change":0.1,"change_percent":0.0525,"direction":"up",
                "prev_close":189.1,"day_change_percent":0.74}, ...}
```
(`prev_close` and `day_change_percent` are the additions from Section 7.) In Massive modes the update rate is the poll interval, not 500 ms; the frontend must not assume a tick every 500 ms.

## 7. Required changes to the existing code

Existing code already satisfies the interface, factory and stream. To implement this design:

| # | Change | File |
|---|---|---|
| 1 | Add `prev_close` to `PriceUpdate`/`PriceCache.update(..., prev_close=None)`; add `day_change`, `day_change_percent`; include in `to_dict()` | `models.py`, `cache.py` |
| 2 | Add `validate_ticker`, `get_prev_closes`, `mode` to `MarketDataSource` with defaults | `interface.py` |
| 3 | Replace the `/1000` timestamp conversion with `to_unix_seconds`; extract price with the fallback chain (5.2) | `massive_client.py` |
| 4 | Add mode probing, `eod` mode via grouped daily, 429 backoff, 401/403 handling | `massive_client.py` |
| 5 | Pass `prev_day.close` / `todays_change_percent` into the cache | `massive_client.py` |
| 6 | Expose `mode` in `/api/health`; optional `MASSIVE_POLL_INTERVAL`, `MARKET_FORCE_SIMULATOR` | `factory.py`, health route |
| 7 | Tests: 403→eod fallback, 429 backoff, timestamp units, missing `last_trade`, ticker validation, weekend lookback | `tests/market/test_massive.py` |

Current limitation to be aware of: with a **free** Massive key the present `MassiveDataSource` would hit 403 on every poll and the cache would stay empty, so the UI would show no prices. Changes 3 and 4 fix this.

## 8. Usage examples

```python
cache = PriceCache()
source = create_market_data_source(cache)
await source.start(["AAPL", "MSFT", "NVDA"])

u = cache.get("AAPL")
print(u.price, u.direction, u.day_change_percent)     # after change 1

if await source.validate_ticker("PYPL"):
    await source.add_ticker("PYPL")

# trade execution
price = cache.get_price("PYPL")
if price is None:
    raise TradeError("No price available for PYPL")

await source.stop()
```

## 9. Testing strategy

- **Contract tests** parametrized over both implementations: lifecycle, add/remove idempotence, cache population within one interval, `remove_ticker` evicts, `stop()` twice is safe.
- **Massive tests** mock `RESTClient` (no network): response parsing for each plan shape, error branches in 5.4, mode selection.
- **Factory tests:** unset, empty, whitespace-only and valid key; `MARKET_FORCE_SIMULATOR`.
- **No live Massive calls in CI.** An opt-in script (`backend/scripts/massive_smoke.py`, runs only if the key is set) prints one real snapshot and one grouped-daily response so attribute names flagged **[unverified]** in MASSIVE_API.md can be confirmed.
