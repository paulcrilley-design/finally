# Phase 2: Trading and Positions (short plan, built without GSD)

Status: awaiting owner approval. Requirements: TRADE-01 to 04, PORT-01, PORT-02, WATCH-05, WATCH-06.

## Rules

- **Quantity:** greater than 0, at most 4 decimal places.
- **Money:** calculated with Python `Decimal`, rounded half up to cents. A buy needs
  `cost <= cash`; a trade whose value rounds to 0.00 is refused. Average cost keeps 4 decimals.
- **Price:** the current cached price (`normalize_ticker()` first). No price means refused, so
  only watched or held tickers can be traded.
- **Sell:** never more than held; selling everything deletes the position row.
- **Atomic:** cash, position and trade log change in one `BEGIN IMMEDIATE` transaction.
- **Unknown price on a held position:** its values and the total show a dash, never a substitute.
- **Restart:** the last price of each tracked ticker is saved (new `last_prices` table) and the
  simulator resumes from it, so P&L does not jump.

## API

- `GET /api/portfolio`: `cash`, `total_value`, `positions[]` (`ticker`, `quantity`, `avg_cost`,
  `price`, `market_value`, `unrealized_pnl`, `pnl_percent`)
- `POST /api/portfolio/trade` `{ticker, side, quantity}`: returns `trade` and `portfolio`
- `POST /api/watchlist` `{ticker}` and `DELETE /api/watchlist/{ticker}`; both then call
  `reconcile_tickers`. A removed ticker with a position keeps being priced.
- Errors: `{"error": {"code", "message"}}` with 400 (rule broken, bad input), 404 (not on the
  watchlist) or 409 (already on it).

## Page

Header shows total value and cash. Below the watchlist (with add and remove controls): a trade bar
(ticker, quantity, Buy, Sell, refusal reason) and a positions table. Values update from the
stream using the server's formulas. openUI components and the existing accessibility rules apply.

## Build order (one run, no stops)

1. Backend: data functions, trade logic, price saving, routes.
2. Frontend: portfolio hook, header values, trade bar, positions table, watchlist controls.
3. Verify: tests, lint, typecheck, build, browser check on a temporary database.
4. README, GSD records, commit and push.

Tests cover the trade and money maths, every refusal leaving data unchanged, concurrent buys not
overspending, the restart price carry-over and the main page flows. No new packages.

Not included: charts, heatmap, value history (Phase 3), chat (Phase 4), Docker (Phase 5).
