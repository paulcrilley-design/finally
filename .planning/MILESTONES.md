# Milestones

## v1.0 MVP (Shipped: 2026-11-27)

**Phases completed:** 5 phases, 15 plans, 0 tasks

**Key accomplishments:**
- Live market terminal: one process serves the page, API and price stream, backed by SQLite
- Market-order trading, watchlist management and portfolio P&L using Decimal maths
- Sparklines, ticker chart, portfolio heatmap and value-over-time chart
- AI chat that trades only after code checks and a second-model review, with a mock mode
- One-command Docker run with saved data and Playwright end-to-end tests

**Closeout:** override_closeout. Requirements 38/38 checked off; open-artifact audit clear.

**Known verification overrides: 5 newly acknowledged, 0 carried forward** (owner chose to close
without further testing):
- Phases 1 to 5 have no GSD verification report; checks are recorded in each phase summary
- No milestone audit was run

**Not checked:** Linux, the start script's `--open`, and live AI chat in the container with a real
key after the final fixes. `planning/PLAN.md` still names LiteLLM (section 9) and the
`finally-data` volume (section 11).

---
