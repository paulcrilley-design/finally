# FinAlly — Team Contracts

Shared interface for all teammates. `PLAN.md` is the product spec; this file fixes the details.
If you need to change a contract, message the lead (`main`) instead of changing it yourself.

## 1. Ownership and working rules

| Area | Owner |
|---|---|
| `backend/db/`, `backend/tests/db/` | Database Engineer |
| `backend/app/` except `llm/`, `backend/tests/api/` | Backend API Engineer |
| `backend/app/llm/`, `backend/tests/llm/` | LLM Engineer |
| `frontend/` | Front-End Engineer |
| `Dockerfile`, `.dockerignore`, `scripts/start_mac.sh`, `scripts/stop_mac.sh` | DevOps Engineer |
| `test/` | Integration Tester |
| `planning/`, `backend/pyproject.toml`, `backend/uv.lock`, `.gitignore`, `.env.example`, `README.md` | Lead |

- One shared working folder: edit only your own area. `backend/app/market/` is finished; change it
  only for a real bug, and tell the lead.
- Do not commit, push, switch branches or stash. The lead handles git.
- Dependencies `litellm` and `pydantic` are already added. Ask the lead for any other Python
  package. Do not run `uv add`.
- Never read, print or edit `.env`. For live LLM calls use `uv run --env-file ../.env ...`.
- Each test subfolder has its own `__init__.py` (and `conftest.py` if needed).
- Run only your own tests: `cd backend && uv run --extra dev pytest tests/<yours>` and
  `uv run --extra dev ruff check <your paths>`.
- Keep code simple and small. No features beyond `PLAN.md` and this file.
- When finished, report in a few lines: files, test result, anything unfinished or deviating.

## 2. Runtime layout and environment

| Variable | Default | Use |
|---|---|---|
| `DB_PATH` | `<project root>/db/finally.db` (`parents[2]` of `backend/db/__init__.py`) | SQLite file |
| `STATIC_DIR` | `<project root>/frontend/out` | Next.js export; skip static serving if missing |
| `LLM_MOCK` | `false` | `true` = no network calls |
| `OPENROUTER_API_KEY` | none | LLM calls |
| `MASSIVE_API_KEY` | empty | Leave empty |

Nothing loads `.env` in code. Container layout: `/app/backend` (code), `/app/static`
(`STATIC_DIR=/app/static`), `/app/db` (named volume `finally-data`). Port 8000.
Local run: `cd backend && uv run uvicorn app.main:app --port 8000 --timeout-graceful-shutdown 3`.
In the container, uvicorn binds `0.0.0.0` and runs a **single worker**.

## 3. Database (`backend/db/`, imported as `import db`)

Synchronous `sqlite3`, one short-lived connection per call, parameterised queries. Timestamps are
ISO 8601 UTC strings. Records are plain dicts. Tickers arrive already normalised.

```python
init_db() -> None                      # idempotent: create tables/indexes, seed if no users
list_user_ids() -> list[str]
get_cash(user_id) -> float
list_watchlist(user_id) -> list[str]                  # in added order
add_watchlist(user_id, ticker) -> bool                # False if already there
remove_watchlist(user_id, ticker) -> bool             # False if not there
list_positions(user_id) -> list[dict]                 # {ticker, quantity, avg_cost, updated_at}
get_position(user_id, ticker) -> dict | None
apply_trade(user_id, ticker, side, quantity, price) -> dict
    # One atomic transaction (BEGIN IMMEDIATE): check, update cash and position, log trade.
    # Returns {id, ticker, side, quantity, price, executed_at}.
    # Raises db.InsufficientCash or db.InsufficientShares and changes nothing.
list_trades(user_id, limit=100) -> list[dict]         # newest first
add_snapshot(user_id, total_value) -> None
list_snapshots(user_id, limit=500) -> list[dict]      # {total_value, recorded_at}, oldest first.
    # Last 7 days. If more than `limit`, downsample evenly, keeping the first and the newest.
prune_snapshots(user_id, days=7) -> None
add_chat_message(user_id, role, content, actions: dict | None = None) -> dict
list_chat_messages(user_id, limit=10) -> list[dict]   # newest `limit`, returned oldest first
    # {id, role, content, actions (decoded dict or None), created_at}
all_tracked_tickers() -> set[str]                     # all users' watchlists and positions
```

Money rules (floats are acceptable): `quantity` is rounded to 4 decimals. Trade value is
`round(quantity * price, 2)`; cash is stored rounded to 2 decimals; a buy needs `value <= cash`.
A buy updates `avg_cost` as the weighted average. A sell keeps `avg_cost`. A position reaching 0
is deleted.

## 4. Backend services (`backend/app/`)

- `app.main:app`, built by `create_app()`. Lifespan: `db.init_db()`, `start_market_data(cache,
  db.all_tracked_tickers())`, snapshot task, and on shutdown stop both.
- `app.state.price_cache`, `app.state.market_source`.
- `app/dependencies.py`: `get_current_user() -> str` returns `"default"`. Nowhere else hardcodes it
  (except DB seed data).
- Snapshot task: every 30 s, for each user, add a snapshot and prune. Also add one at startup and
  after each trade. Skip a snapshot if any position has no price.
- `app/main.py` includes `create_stream_router(cache)`, the API routers and
  `app.llm.create_chat_router()`, then mounts static files at `/` last (`html=True`). Unknown
  `/api/*` paths return a 404 JSON error.

Service functions (used by the REST routes **and** the chat). `state` is `app.state`.

```python
# app/services/errors.py
class ServiceError(Exception):  # ServiceError(code: str, message: str, status: int = 400)

# app/services/portfolio.py
get_portfolio(state, user_id) -> dict                       # shape of GET /api/portfolio
check_trade(state, user_id, ticker, side, quantity) -> float
    # No writes. Returns the live price, or raises ServiceError.
async execute_trade(state, user_id, ticker, side, quantity) -> dict
    # shape of the POST trade response; also snapshots and reconciles tickers

# app/services/watchlist.py
get_watchlist(state, user_id) -> dict                       # shape of GET /api/watchlist
check_change(state, user_id, ticker, action) -> str         # action "add"|"remove"; returns
                                                            # normalised ticker or raises
async add_ticker(state, user_id, ticker) -> dict            # returns one watchlist item
async remove_ticker(state, user_id, ticker) -> None
```

Services normalise tickers. After any watchlist or trade change:
`await reconcile_tickers(state.market_source, db.all_tracked_tickers())`.

## 5. REST API

### Errors (every 4xx/5xx under `/api`, including request validation)

```json
{"error": {"code": "insufficient_cash", "message": "Human readable sentence."}}
```

| Code | Status |
|---|---|
| `invalid_request` | 422 |
| `invalid_ticker`, `invalid_quantity`, `invalid_side` | 400 |
| `no_price`, `insufficient_cash`, `insufficient_shares` | 400 |
| `already_watching` | 409 |
| `not_watching`, `not_found` | 404 |

A ticker with no live price is rejected (`no_price`). Off-watchlist trades are allowed if priced.
Quantity must be finite and above 0 after rounding to 4 decimals.

### `GET /api/health`
```json
{"status": "ok", "market": {"mode": "simulator", "degraded": false, "tickers": 10}, "llm_mock": false}
```
`status` is `"degraded"` when `market.degraded` is true. Always HTTP 200.

### `GET /api/portfolio`
```json
{"cash_balance": 8100.0, "total_value": 10012.5, "positions_value": 1912.5,
 "unrealized_pnl": 12.5,
 "positions": [{"ticker": "AAPL", "quantity": 10.0, "avg_cost": 190.0, "current_price": 191.25,
   "market_value": 1912.5, "unrealized_pnl": 12.5, "unrealized_pnl_percent": 0.6579,
   "weight": 1.0}]}
```
`weight` is the share of `positions_value` (0 to 1). If a position has no price, its
`current_price`, `market_value`, `unrealized_pnl`, `unrealized_pnl_percent` and `weight` are
`null` and it is left out of the totals.

### `POST /api/portfolio/trade`
Request `{"ticker": "AAPL", "quantity": 10, "side": "buy"}` (side `"buy"`|`"sell"`). Response 200:
```json
{"trade": {"id": "...", "ticker": "AAPL", "side": "buy", "quantity": 10.0, "price": 190.0,
           "executed_at": "2026-11-27T10:00:00+00:00"},
 "portfolio": { "...": "same shape as GET /api/portfolio" }}
```

### `GET /api/portfolio/history`
```json
{"history": [{"total_value": 10000.0, "recorded_at": "2026-11-27T10:00:00+00:00"}]}
```

### `GET /api/watchlist`
```json
{"tickers": [{"ticker": "AAPL", "price": 191.25, "previous_price": 191.1, "timestamp": 1780000000.5,
  "direction": "up", "prev_close": 190.0, "day_change": 1.25, "day_change_percent": 0.6579}]}
```
All fields except `ticker` are `null` when unpriced.

### `POST /api/watchlist`
Request `{"ticker": "PYPL"}`. Response 201: one item in the shape above.

### `DELETE /api/watchlist/{ticker}`
Response 204.

### `GET /api/stream/prices` (already built)
SSE `data:` events, each a map of **all** tracked tickers (includes held, unwatched ones):
```json
{"AAPL": {"ticker": "AAPL", "price": 191.25, "previous_price": 191.1, "timestamp": 1780000000.5,
  "change": 0.15, "change_percent": 0.0785, "direction": "up", "prev_close": 190.0,
  "day_change": 1.25, "day_change_percent": 0.6579}}
```
Flash a price only when that ticker's `timestamp` changes.

## 6. Chat (`backend/app/llm/`)

`create_chat_router() -> APIRouter` (exported from `app.llm`) serves `POST /api/chat`.

Request `{"message": "buy 5 AAPL"}` (non-empty after trimming, max 2000 characters, else 422
`invalid_request`). Response is **always 200** for a valid request:

```json
{"message": "Assistant text, with rejection reasons appended.",
 "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5.0, "status": "executed",
   "price": 191.25, "reason": null,
   "review": {"verdict": "approve", "reason": "Matches the request."}}],
 "watchlist_changes": [{"ticker": "PYPL", "action": "add", "status": "rejected",
   "reason": "Already on the watchlist.", "review": null}],
 "error": null}
```

- `status` is `"executed"` or `"rejected"`. `review` is `null` if the action never reached the
  reviewer. `price` is `null` unless executed.
- `error` is `null`, `"llm_unavailable"` (proposer failed in any way, including a missing key:
  clear message, both action lists empty) or `"review_failed"` (all reviewed actions rejected).
- A failed review blocks trades **and** watchlist changes. A missing verdict counts as reject.
- Order: validate (`check_trade` / `check_change`), review the survivors, then execute watchlist
  changes first and trades second, each independently.
- Store the user message and the assistant reply with `db.add_chat_message`; the assistant
  `actions` is `{"trades": [...], "watchlist_changes": [...], "error": ...}`.
- Blocking LLM calls must not stall the event loop (use `litellm.acompletion` or a thread), and
  need a timeout.

### Mock mode (`LLM_MOCK=true`), case-insensitive, deterministic

| User message contains | Proposer returns |
|---|---|
| `buy <qty> <TICKER>` / `sell <qty> <TICKER>` (repeatable) | those trades |
| `add <TICKER>` / `remove <TICKER>` (repeatable) | those watchlist changes |
| none of the above | no actions |

Message text: `"Mock response: here is your request."` with actions, otherwise
`"Mock response: your portfolio looks balanced."`. The mock reviewer approves everything, unless
the message contains the word `reject`, then it rejects everything with reason
`"Mock reviewer rejection."` and `error` stays `null`.

## 7. Front end and test selectors

Single page, static export (`output: 'export'`, built to `frontend/out`). `npm run build` and
`npm test` (Vitest, run once, no watch) must work. Commit `package-lock.json`. Node 20 in Docker.
The chat panel shows messages from the current page session (there is no history endpoint).
Header total value updates live from cash plus positions at SSE prices. Refresh portfolio,
watchlist and history after trades and chat actions, and history about every 30 s.

Required `data-testid` values (`{T}` = ticker):

| Selector | Element |
|---|---|
| `header-total-value`, `header-cash` | header amounts, formatted like `$10,000.00` |
| `connection-status` | with attribute `data-state="connected"\|"reconnecting"\|"disconnected"` |
| `watchlist` | watchlist panel |
| `watchlist-row-{T}` | row; clicking selects the ticker |
| `watchlist-price-{T}` | price text, `$191.25` |
| `watchlist-remove-{T}` | remove button |
| `watchlist-add-input`, `watchlist-add-button` | add form |
| `main-chart` | with attribute `data-ticker="{T}"` |
| `trade-ticker`, `trade-quantity`, `trade-buy`, `trade-sell` | trade bar |
| `trade-message` | success or error text after a trade |
| `positions-table`, `position-row-{T}`, `position-quantity-{T}` | positions |
| `heatmap`, `heatmap-cell-{T}` | cell has `data-pnl="profit"\|"loss"\|"flat"` |
| `pnl-chart` | with attribute `data-points="<count>"` |
| `chat-panel`, `chat-toggle`, `chat-input`, `chat-send`, `chat-loading` | chat |
| `chat-message-user`, `chat-message-assistant` | one per message |
| `chat-action` | one per action, with `data-status="executed"\|"rejected"` |

The chat panel is open by default on desktop widths.
