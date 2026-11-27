# Phase 3: Price and Portfolio Charts (short plan, built without GSD)

Status: approved and built (see 03-SUMMARY.md). Requirements: WATCH-03, WATCH-04, PORT-03, PORT-04.

## New packages

`recharts@^3.11.1` (github.com/recharts/recharts) and its peer `react-is@^19` (facebook/react).
Recharts is the only charting library, for the treemap too.

## Rules

- **Price history:** kept in the browser only, from page load, the last 1,800 points (about 15
  minutes) per ticker. Repeated timestamps are ignored. A reload starts empty.
- **Sparklines:** one per watchlist row.
- **Main chart:** clicking a ticker name selects it. The first watched ticker is selected at the
  start, and again if the selected one is removed.
- **Value snapshots:** per user at startup, every 30 seconds and immediately after each trade
  (in the trade's transaction). Skipped while any held price is unknown.
- **Retention:** snapshots older than 7 days are deleted.
- **History API:** `GET /api/portfolio/history` returns `{"history": [{recorded_at, total_value}]}`,
  oldest first, thinned to at most 500 points and always including the latest.
- **Heatmap:** one rectangle per position, sized by market value (cash excluded), teal-ink for
  profit, orange-ink for loss, gray for flat, labelled with ticker and signed % change.

## Page

Main chart above the trade bar; heatmap and value chart below the positions table. openUI chart
colours, text alternatives for screen readers, no animation under reduced motion, and empty-state
messages while there is nothing to draw.

## Build order (one run, no stops)

1. Backend: snapshots, retention, history route.
2. Frontend: price history, sparklines, main chart, heatmap, value chart.
3. Verify: tests, lint, typecheck, build, browser check on a temporary database.
4. README, GSD records, commit and push.

Tests cover snapshot timing, retention, thinning, history rules, selection and the heatmap data.

Not included: AI chat (Phase 4), Docker and the tablet and phone layout pass (Phase 5).
