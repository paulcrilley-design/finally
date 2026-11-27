---
phase: 02-trading-and-positions
status: complete
requirements-completed: [TRADE-01, TRADE-02, TRADE-03, TRADE-04, PORT-01, PORT-02, WATCH-05, WATCH-06]
---

# Phase 2 Summary: trading and positions

## Built

- Backend: `db/portfolio.py` (Decimal, one `BEGIN IMMEDIATE` transaction), portfolio and
  watchlist routes, one error shape, `last_prices` table and simulator resume.
- Page: header total and cash, trade bar, positions table, add and remove tickers.

## Verification

- Backend 227 passed, ruff clean; frontend 67 passed, lint, typecheck and build passed.
- Both sides test the same valuation cases (`backend/tests/fixtures/valuation_cases.json`).
- Browser, temporary database: buys, sell, four refusals, duplicate add, add and remove, a held
  ticker staying priced after removal, restart and reconnect, no page scroll at 375 px.

## Notes

- One addition to the plan: a whole position can be sold even if it is worth under a cent.
- Prices are saved every 5 s, at shutdown and with each trade, so a crash can lose up to 5 s.
- At 375 px the positions table scrolls sideways inside its panel (layout pass is Phase 5).
