# Market Simulator: Approach and Code Structure

The simulator is the default market data source (used whenever `MASSIVE_API_KEY` is unset). It produces realistic, correlated, continuously moving prices for any ticker with no external dependencies. It implements `MarketDataSource` (see MARKET_INTERFACE.md) and writes to the shared `PriceCache`.

Implemented in `backend/app/market/simulator.py` and `seed_prices.py`; tests in `backend/tests/market/test_simulator*.py`. This document describes the approach and the intended structure, and notes where the design extends the current code.

---

## 1. Goals

- Look and feel like a live market: constant small moves, occasional dramatic ones, sectors that move together.
- Deterministic enough to test; random enough to be interesting.
- Zero cost: no network, no keys, runs in-process as one asyncio task.
- Handle tickers added at runtime (including ones never seen before).
- Cheap: ~10-50 tickers every 500 ms is trivial.

Non-goals: realistic order books, volume, intraday seasonality, fundamentals.

## 2. Price model: geometric Brownian motion

Each ticker follows GBM, the standard model for equity prices (always positive, returns roughly log-normal):

```
S(t+dt) = S(t) · exp( (μ − σ²/2)·dt + σ·√dt·Z )
```

| Symbol | Meaning | Source |
|---|---|---|
| `S` | price | seed price, then evolves |
| `μ` | annualized drift | per-ticker, ~3-8% |
| `σ` | annualized volatility | per-ticker, 17-50% |
| `dt` | step as a fraction of a trading year | constant, see below |
| `Z` | standard normal draw, **correlated across tickers** | Section 3 |

**Time step.** Ticks are 500 ms apart, and a trading year is `252 days × 6.5 h × 3600 s = 5,896,800 s`, so `dt = 0.5 / 5,896,800 ≈ 8.48e-8`. A 25%-vol stock then moves about `0.25·√dt ≈ 0.007%` per tick (about 1.3 cents on $190), which looks like believable tape. Over a simulated 6.5-hour session the standard deviation of the move is about σ/√252 ≈ 1.6%. The drift term is negligible tick to tick but keeps long runs plausible.

Prices are rounded to 2 decimals on output only; the internal state stays full precision so rounding does not bias the walk.

## 3. Correlated moves

Real stocks move together. We build a correlation matrix and use its Cholesky factor to correlate the normal draws:

1. `ρ_ij` from sector rules (`seed_prices.py`):
   - both tech (AAPL, GOOGL, MSFT, AMZN, META, NVDA, NFLX): **0.6**
   - both finance (JPM, V): **0.5**
   - TSLA with anything: **0.3** (it behaves idiosyncratically)
   - cross-sector or unknown ticker: **0.3**
2. `C = cholesky(R)` (lower triangular, `R = C·Cᵀ`).
3. Each tick draw `z ~ N(0, I)` of length n, then `z_corr = C · z`. Each `z_corr[i]` is still standard normal but correlated as specified.

`R` is positive definite for these constant-correlation blocks (all off-diagonals in [0.3, 0.6], so it is diagonally dominant enough for any n). It is rebuilt whenever a ticker is added or removed; cost O(n²) for the matrix plus O(n³) for Cholesky, negligible for n < 50. If `cholesky` ever raised `LinAlgError` (it shouldn't with these constants), the fix is to fall back to independent draws and log a warning.

## 4. Random events

To make the demo dramatic, each tick each ticker has a **0.1%** chance (`event_probability=0.001`) of a shock: a one-off jump of **2-5%** up or down (uniform magnitude, random sign), applied multiplicatively after the GBM step. With 10 tickers at 2 ticks/s that is roughly one event every 50 seconds across the watchlist. Events are logged at DEBUG and are not correlated across tickers.

## 5. Tickers and parameters

`seed_prices.py` holds:

| Constant | Content |
|---|---|
| `SEED_PRICES` | Starting price for the 10 default tickers (AAPL 190, GOOGL 175, MSFT 420, AMZN 185, TSLA 250, NVDA 800, META 500, JPM 195, V 280, NFLX 600) |
| `TICKER_PARAMS` | `{sigma, mu}` per default ticker (e.g. TSLA σ=0.50, NVDA σ=0.40 μ=0.08, V σ=0.17) |
| `DEFAULT_PARAMS` | `σ=0.25, μ=0.05` for any other ticker |
| `CORRELATION_GROUPS` and `*_CORR` | Sector sets and coefficients (Section 3) |

**Unknown tickers** (e.g. a user adds PYPL): start at a random price in $50-$300 with default parameters. This answers PLAN.md Section 13, question 3. A small extension worth making: a `KNOWN_PRICES` table with a few dozen popular tickers (PYPL, AMD, DIS, BA, KO, ...) so well-known symbols start near realistic prices, with fallback to the random draw.

**Day baseline.** The simulator treats each ticker's price at process start as its "previous close" (`get_prev_closes`), so the watchlist's daily change % starts at 0% and drifts, which is intuitive for a demo. Optionally persist it per calendar day so restarts do not reset it.

## 6. Code structure

```
backend/app/market/
├── seed_prices.py     constants only: prices, per-ticker params, correlation groups/values
├── simulator.py
│   ├── GBMSimulator          pure math/state, no asyncio, no cache (easy to unit test)
│   └── SimulatorDataSource   asyncio wrapper implementing MarketDataSource
├── cache.py           PriceCache (shared; the simulator is a producer)
├── interface.py       MarketDataSource ABC
└── factory.py         picks Simulator vs Massive
```

### 6.1 `GBMSimulator` (pure, synchronous)

```python
class GBMSimulator:
    TRADING_SECONDS_PER_YEAR = 252 * 6.5 * 3600
    DEFAULT_DT = 0.5 / TRADING_SECONDS_PER_YEAR

    def __init__(self, tickers, dt=DEFAULT_DT, event_probability=0.001): ...
    def step(self) -> dict[str, float]         # advance all tickers one tick; returns rounded prices
    def add_ticker(self, ticker) -> None       # seed price + params, rebuild Cholesky
    def remove_ticker(self, ticker) -> None
    def get_price(self, ticker) -> float | None
    def get_tickers(self) -> list[str]
```

`step()` in outline:

```python
z = np.random.standard_normal(n)
z = self._cholesky @ z if self._cholesky is not None else z
for i, t in enumerate(self._tickers):
    mu, sigma = self._params[t]["mu"], self._params[t]["sigma"]
    self._prices[t] *= math.exp((mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z[i])
    if random.random() < self._event_prob:
        self._prices[t] *= 1 + random.uniform(0.02, 0.05) * random.choice((-1, 1))
    out[t] = round(self._prices[t], 2)
```

Design choice: keeping the math in a class with no I/O means tests can step it thousands of times synchronously and assert statistical properties.

### 6.2 `SimulatorDataSource` (asyncio adapter)

```python
class SimulatorDataSource(MarketDataSource):
    def __init__(self, price_cache, update_interval=0.5, event_probability=0.001): ...
    async def start(self, tickers):   # build GBMSimulator, seed cache immediately, create task
    async def stop(self):             # cancel task, await it, swallow CancelledError
    async def add_ticker(self, t):    # sim.add_ticker + immediate cache seed
    async def remove_ticker(self, t): # sim.remove_ticker + cache.remove
    def get_tickers(self): ...
    async def _run_loop(self):        # while True: step -> cache.update each -> sleep(interval)
```

Key behaviours:
- **Seeds the cache in `start()` and `add_ticker()`** so the SSE stream and trade validation have a price immediately, with no 500 ms gap.
- The loop catches and logs exceptions per tick, so one bad step never kills the stream.
- Uses `await asyncio.sleep(interval)` (drift of a few ms is irrelevant here).
- The first update for a ticker has `previous_price == price`, so direction is `flat`; thereafter the cache computes direction per tick.

### 6.3 Normalising input

Ticker symbols should be `.upper().strip()`-ed at the interface boundary. The Massive source does this in `add_ticker`; the simulator should do the same (a small consistency fix) so `"aapl"` and `"AAPL"` do not become two tickers.

## 7. Tuning parameters

| Parameter | Default | Effect |
|---|---|---|
| `update_interval` | 0.5 s | Tick cadence; SSE sends at most this often |
| `dt` | 8.48e-8 | Per-tick variance; keep consistent with the interval |
| `event_probability` | 0.001 | Shock rate; set 0 for calm tests |
| `sigma`, `mu` | per ticker | Volatility and trend |
| correlations | 0.3-0.6 | Strength of co-movement |

For a livelier demo, raise `dt` (e.g. ×10) rather than sigma: moves are bigger per tick while annualized parameters stay meaningful. Seed `np.random` and `random` for reproducible runs (E2E tests with `LLM_MOCK=true` can also set a `SIM_SEED` env var; to add).

## 8. Testing

Existing tests (17 in `test_simulator.py`, 10 in `test_simulator_source.py`) cover price positivity, add/remove, Cholesky rebuild, events, and the async lifecycle. Additional properties worth asserting:

- **Positivity:** 100k steps never produce a price ≤ 0.
- **Volatility calibration:** over many steps the standard deviation of log returns divided by `√dt` is close to σ (within ~5%) with events disabled.
- **Correlation:** empirical correlation of returns for two tech tickers ≈ 0.6 (±0.05) over ~20k steps; TSLA vs MSFT ≈ 0.3.
- **Events:** with `event_probability=1.0`, every step moves a ticker by ≥ 2%.
- **Determinism:** same seed gives identical series.
- **Unknown ticker** starts in $50-$300 and uses default params; adding it does not disturb existing prices.
- **Case/whitespace** normalisation (after change in 6.3).

## 9. Limitations and extension ideas

- Constant parameters: no volatility clustering or mean reversion; fat tails come only from the event shocks. A GARCH-style or regime switch is possible but unneeded.
- No market hours: the simulator runs 24/7, so "daily change %" is relative to process start (Section 5).
- Correlations are crude sector blocks; a real covariance estimate would need data we deliberately avoid.
- Price history is not stored on the backend; sparklines are built client-side from the SSE stream. If a backfill endpoint is added, the simulator could generate a synthetic history by running GBM backwards from the current price.
