# Massive API Reference (formerly Polygon.io)

Research notes on the Massive REST API for retrieving real-time and end-of-day stock prices for multiple tickers, with Python examples. Written for FinAlly; only the endpoints we use or might use are covered.

Sources: the official docs at `massive.com/docs/rest/stocks/...` (fetched 2026-11-25), the Massive knowledge base, and the `massive-com/client-python` README. Items marked **[unverified]** were not confirmed in those sources and must be checked against a live key before relying on them.

---

## 1. Overview

- Polygon.io was renamed **Massive** (announced 2025-10-30). Existing keys, accounts and integrations continue to work.
- Base URL: `https://api.massive.com`. The legacy `https://api.polygon.io` host keeps working "for an extended period".
- Python package: `massive` (`pip install -U massive`, or `uv add massive`). Requires Python 3.10+. The project already depends on `massive>=1.0.0`.
- All data endpoints are REST/JSON. WebSocket streaming exists but FinAlly deliberately uses REST polling (see PLAN.md Section 6).

## 2. Authentication

Two equivalent methods:

```bash
# Query parameter
curl "https://api.massive.com/v2/aggs/ticker/AAPL/prev?apiKey=$MASSIVE_API_KEY"

# Header (preferred: keeps the key out of URLs and logs)
curl -H "Authorization: Bearer $MASSIVE_API_KEY" \
     "https://api.massive.com/v2/aggs/ticker/AAPL/prev"
```

The Python client sends the Bearer header. `RESTClient(api_key=...)` takes the key explicitly. The README does not document reading an env var, so the app must pass `MASSIVE_API_KEY` itself (our factory already does).

Note that `next_url` values in paginated responses do **not** contain the key; append `apiKey` or send the header again when following them (the Python client does this for you).

## 3. Plans, limits and data recency

This is the most important section for design, because it decides which endpoints work for a given key.

| Plan (Stocks) | Call limit | Data recency | Aggregates history | Snapshots | Last trade | Last quote |
|---|---|---|---|---|---|---|
| Basic (free) | 5 requests/min | End of day | 2 years | **No access** | No | No |
| Starter | Unlimited | 15-min delayed | 5 years | Yes | No | No |
| Developer | Unlimited | 15-min delayed | 10 years | Yes | Yes (delayed) | No |
| Advanced | Unlimited | Real-time | All (to 2003) | Yes | Yes | Yes |
| Business | Unlimited | Real-time | All | Yes | Add-on only | Add-on only |

Sources and caveats:
- Recency, history and endpoint access per plan come from the docs pages for each endpoint.
- The 5/min limit is from the Massive knowledge base: "Five requests a minute per asset class you have not subscribed to, and no limit on the ones you have." Limits are counted per asset class, not per account. Paid tiers are unlimited for their product.
- Exact prices and plan names change; the pricing page did not render for our fetch. Check `massive.com/pricing`. **[unverified]** for Starter/Developer limits beyond "unlimited".
- Snapshot docs say Stocks Basic has no access, and the KB says "Starter and above. The free Basic plans do not include the snapshot."

**Consequence for FinAlly:** a free key can only use the aggregates endpoints (Section 5), which give end-of-day data. A free key cannot power the current snapshot-based poller. See MARKET_DATA_DESIGN.md Section 7.4 for how we handle this.

### Errors

| HTTP | Body | Meaning |
|---|---|---|
| 400 | | Usually more than 250 tickers in `ticker.any_of` on `/v3/snapshot` |
| 401 | not documented | Missing or invalid key ("authorization error") **[unverified]** exact code |
| 403 | `{"status":"NOT_AUTHORIZED","message":"Your plan doesn't include this data timeframe..."}` | Endpoint or recency not in your plan. Retrying an older date often works |
| 429 | `{"status":"ERROR","error":"You've exceeded the maximum requests per minute..."}` | Rate limit (free tier) |

## 4. Real-time prices: snapshots (Starter and above)

### 4.1 Full market snapshot (primary endpoint for FinAlly)

```
GET /v2/snapshot/locale/us/markets/stocks/tickers
```

| Param | Type | Notes |
|---|---|---|
| `tickers` | string, optional | Comma-separated, **case-sensitive**: `AAPL,TSLA,GOOG`. Empty returns the whole market (10,000+ tickers) |
| `include_otc` | bool, default false | |

One call returns all requested tickers, so polling a whole watchlist costs one request. No pagination or ticker cap is documented for this endpoint (the 250 cap applies to `/v3/snapshot`).

Response:

```json
{
  "status": "OK",
  "count": 1,
  "tickers": [{
    "ticker": "AAPL",
    "todaysChange": 0.98,
    "todaysChangePerc": 0.82,
    "updated": 1605195918306274000,
    "day":     {"o": 119.62, "h": 120.53, "l": 118.81, "c": 120.4229, "v": 28727868, "vw": 119.725},
    "min":     {"o": 120.435, "h": 120.468, "l": 120.37, "c": 120.4201, "v": 270796, "vw": 120.4129, "n": 762, "t": 1684428720000, "av": 28724441},
    "prevDay": {"o": 117.19, "h": 119.63, "l": 116.44, "c": 119.49, "v": 110597265, "vw": 118.4998},
    "lastTrade": {"p": 120.47, "s": 236, "t": 1605195918306274000, "x": 10, "i": "4046", "c": [14, 41]},
    "lastQuote": {"p": 120.46, "s": 8, "P": 120.47, "S": 4, "t": 1605195918507251700}
  }]
}
```

Field notes:
- `day`: today's bar so far. `min`: latest minute bar. `prevDay`: previous trading day's bar (its `c` is the previous close, the right baseline for "daily change %").
- `todaysChange` / `todaysChangePerc`: change versus previous close, computed by Massive.
- `lastTrade` is present **only if the plan includes trades**; `lastQuote` only if it includes quotes. On Starter it may be absent, so code must fall back to `min.c` or `day.c`.
- Sub-field letters are not defined on the page; the meanings above follow the same convention as the aggregates endpoints (`o,h,l,c,v,vw,n`) and the last-trade endpoint (`p` price, `s` size, `t` timestamp). **[unverified]** for `av`, `dv`, `dav`.
- `updated` and `lastTrade.t` look like Unix **nanoseconds** in the raw JSON samples, while `min.t` is Unix milliseconds. The page does not state units. **[unverified]**: normalize by magnitude (see MARKET_DATA_DESIGN.md Section 7.3).
- A ticker the plan/market doesn't know may be silently absent from `tickers`; don't assume the count matches the request.
- Freshness: "Snapshot data is cleared daily at 3:30 AM EST and begins to repopulate as exchanges report new data, which can start as early as 4:00 AM EST." Between those times the snapshot can be empty or stale, so poll code must tolerate missing tickers.

### 4.2 Single ticker snapshot

```
GET /v2/snapshot/locale/us/markets/stocks/tickers/{stocksTicker}
```
Same object as one element above, wrapped as `{"status": "OK", "request_id": "...", "ticker": {...}}`. Useful for validating a ticker the user adds.

### 4.3 Unified snapshot

```
GET /v3/snapshot?ticker.any_of=AAPL,MSFT&type=stocks&limit=250
```
Multi-asset. `ticker.any_of` accepts at most 250 symbols (251 returns HTTP 400); `limit` default 10, max 250; paginated via `next_url`. Results use snake_case: `last_trade.price`, `last_quote.bid/ask`, `last_minute`, `market_status`, and a `session` object (`open, high, low, close, volume, change, change_percent, previous_close, early_trading_change, late_trading_change`). Unknown tickers come back as a row with `"error": "NOT_FOUND"` instead of being dropped, which makes validation easy. We prefer the v2 full-market endpoint for the poller because it has no ticker cap and is what the code already uses; `/v3/snapshot` is a reasonable alternative.

### 4.4 Last trade and last quote

```
GET /v2/last/trade/{ticker}   -> results: {T, p price, s size, t SIP ts (ns), x exchange, c conditions, ...}
GET /v2/last/nbbo/{ticker}    -> results: {T, p bid, s bid size, P ask, S ask size, t ns, ...}
```
One ticker per call, so they are poor for multi-ticker polling. Last trade needs Developer or above; last quote needs Advanced.

## 5. End-of-day prices: aggregates (all plans, including free)

### 5.1 Previous day bar (one ticker)

```
GET /v2/aggs/ticker/{ticker}/prev?adjusted=true
```
```json
{"ticker":"AAPL","adjusted":true,"queryCount":1,"resultsCount":1,"status":"OK",
 "results":[{"T":"AAPL","o":115.55,"h":117.59,"l":114.13,"c":115.97,"v":131704427,"vw":116.3058,"t":1605042000000}]}
```
`c` is the previous close. One call per ticker (10 tickers = 10 calls, which exceeds the free 5/min, so use 5.2 instead for more than a handful).

### 5.2 Daily market summary (grouped daily): all tickers in one call

```
GET /v2/aggs/grouped/locale/us/market/stocks/{YYYY-MM-DD}?adjusted=true&include_otc=false
```
Returns one bar for every US stock for that date, with `T` (ticker), `o,h,l,c,v,vw,n,t`. This is the **best free-tier endpoint**: one request covers the entire watchlist. The date must be a past trading day (the current day's data is not available on Basic); weekends/holidays return an empty result, so step back until `resultsCount > 0`. The payload is large (several MB), so filter client-side and cache it. `t` is documented as the end of the window here but the start of window on custom bars **[unverified]**; do not rely on it.

### 5.3 Custom bars (history for charts)

```
GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}?adjusted=true&sort=asc&limit=5000
```
- `timespan`: `minute`, `hour`, `day`, `week`, `month`, `quarter`, `year` (allowed values are not listed on the page; these are the documented Polygon values).
- `from`/`to`: `YYYY-MM-DD` or Unix ms, both inclusive.
- `limit`: default 5000, max 50000; it caps base aggregates queried, not bars returned, so long ranges can come back truncated. Follow `next_url`.
- Result fields: `o h l c v vw n` and `t` (Unix ms, start of window, Eastern session). Windows with no trades produce no bar.
- Use for backfilling a main chart when a ticker is selected (not required for the MVP; the plan accumulates charts from the stream).

### 5.4 Daily ticker summary (open/close)

```
GET /v1/open-close/{ticker}/{YYYY-MM-DD}?adjusted=true
```
Flat object: `symbol, from, open, high, low, close, volume, preMarket, afterHours, status`. One ticker per call; the grouped endpoint is better for many tickers.

## 6. Python client examples

The client is synchronous. In asyncio code, run it with `asyncio.to_thread` (as `MassiveDataSource` does).

```python
import os
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

client = RESTClient(api_key=os.environ["MASSIVE_API_KEY"])
```

### 6.1 Live prices for several tickers (one call)

```python
snaps = client.get_snapshot_all(
    market_type=SnapshotMarketType.STOCKS,
    tickers=["AAPL", "MSFT", "NVDA"],
)
for s in snaps:
    # last_trade exists only on plans that include trades; fall back otherwise
    price = s.last_trade.price if s.last_trade else (s.min.close if s.min else s.day.close)
    print(s.ticker, price, s.todays_change_percent, s.prev_day.close)
```
Attribute names above follow the client's model naming (`last_trade.price`, `last_trade.timestamp`, `day.close`, `prev_day.close`, `todays_change_percent`). The README does not list model attributes, so confirm by inspecting a returned object (`print(snaps[0])`) once with a real key. **[unverified]**

### 6.2 End-of-day closes for many tickers (works on the free tier)

```python
from datetime import date, timedelta

def last_closes(client, tickers, max_lookback=7):
    wanted = {t.upper() for t in tickers}
    day = date.today() - timedelta(days=1)
    for _ in range(max_lookback):
        bars = client.get_grouped_daily_aggs(day.isoformat(), adjusted=True)
        hits = {b.ticker: b.close for b in bars if b.ticker in wanted}
        if hits:
            return day, hits
        day -= timedelta(days=1)       # weekend / holiday / not yet published
    return None, {}
```

### 6.3 Previous close for one ticker

```python
prev = client.get_previous_close_agg("AAPL")   # list with one agg
print(prev[0].close)
```

### 6.4 History for a chart

```python
bars = [b for b in client.list_aggs("AAPL", 1, "day", "2026-01-01", "2026-11-24", limit=50000)]
closes = [(b.timestamp, b.close) for b in bars]   # timestamp: Unix ms
```
`list_aggs` follows `next_url` automatically (pagination is on by default; `limit` is page size). `get_aggs` returns a single page, so long minute ranges silently truncate.

### 6.5 Raw HTTP alternative (no SDK)

```python
import httpx
r = httpx.get(
    "https://api.massive.com/v2/snapshot/locale/us/markets/stocks/tickers",
    params={"tickers": "AAPL,MSFT,NVDA"},
    headers={"Authorization": f"Bearer {key}"},
    timeout=10,
)
r.raise_for_status()
for t in r.json().get("tickers", []):
    price = (t.get("lastTrade") or {}).get("p") or (t.get("min") or {}).get("c") or t["day"]["c"]
```

## 7. Polling budget

| Plan | Endpoint | Calls per poll | Safe interval |
|---|---|---|---|
| Free | grouped daily, cached for the day | 1 per day (+1 per retry) | Once at startup, then at most hourly |
| Free (alternative) | `prev` per ticker | N tickers | N <= 5 per minute only |
| Starter/Developer | full market snapshot | 1 | 5-15 s (data is 15-min delayed, so faster adds nothing) |
| Advanced | full market snapshot | 1 | 2-5 s |

Free-tier prices are previous closes and do not change intraday. The UI should show them as static and say so (the existing price flash only fires on change).

## 8. Gotchas checklist

- Tickers are case-sensitive; always upper-case.
- Wrap every call in error handling for 401/403/429; never let a poll error kill the loop.
- Markets closed: snapshots hold the last values and `updated` does not advance, so prices will not change at weekends. This is expected.
- Pre-market/after-hours prices can appear in `lastTrade` while `day` still shows the regular session.
- Do not log the API key or URLs containing `apiKey=`.
- Timestamps mix nanoseconds, milliseconds and seconds across endpoints; normalize on ingest.
- Documentation contained a few typos and a forward-dated note (the `overnight_trading` session "new as of 2026-12-07"), so treat the docs as slightly noisy and verify with a live call.
