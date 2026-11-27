---
phase: 03-price-and-portfolio-charts
status: complete
requirements-completed: [WATCH-03, WATCH-04, PORT-03, PORT-04]
---

# Phase 3 Summary: price and portfolio charts

## Built

- Backend: `db/snapshots.py`, snapshots at startup, every 30 s and in each trade's transaction,
  7-day retention, `GET /api/portfolio/history` (at most 500 points).
- Page: sparklines, price chart with ticker selection, heatmap and value chart (Recharts).
- Packages (owner approved): `recharts`, `react-is` (npm lists its repository as `react/react`).

## Verification

- Backend 233 passed, ruff clean; frontend 78 passed, lint, typecheck and build passed.
- Browser, temporary database: sparklines and charts draw, selection switches the chart, heatmap
  tiles and value points appear, history survives a reload, no console warnings, no page scroll
  at 375 px.
- The flat-series axis fix is covered by a unit test; its labels were not re-inspected visually.

## Notes

- Sparklines are hidden below 640 px to fit the watchlist (layout pass is Phase 5).
- Very small heatmap tiles show only the ticker, or nothing; a screen-reader list has them all.
