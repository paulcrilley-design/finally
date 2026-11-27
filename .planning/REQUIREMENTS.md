# Requirements: FinAlly

**Defined:** 2026-11-27
**Core Value:** The trading terminal works: prices stream live, buys and sells fill correctly, and the portfolio, cash and P&L numbers are right.

Source specification: `planning/PLAN.md`.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Platform and Data

- [ ] **APP-01**: User can open `http://localhost:8000` with no login and get the app, with the pages and API served by one process
- [ ] **APP-02**: A health endpoint reports whether the app and market data are working
- [ ] **APP-03**: A fresh start creates the database with $10,000 cash and the 10 default tickers
- [ ] **APP-04**: Cash, positions, watchlist, trades and chat survive a restart
- [ ] **APP-05**: User identity comes from one function and every user-owned record carries `user_id`

### Watchlist and Market View

- [ ] **WATCH-01**: User can see watched tickers with live price and daily change %
- [ ] **WATCH-02**: User sees a fading flash and ▲/▼ arrow when a price changes
- [ ] **WATCH-03**: User can see a sparkline per ticker, built up since page load
- [ ] **WATCH-04**: User can click a ticker to see its larger price chart
- [ ] **WATCH-05**: User can add a ticker
- [ ] **WATCH-06**: User can remove a ticker; one with an open position keeps being priced
- [ ] **WATCH-07**: User can see connection status (connected, reconnecting, disconnected), and the stream reconnects by itself

### Trading

- [ ] **TRADE-01**: User can buy shares, including fractions, at the current price
- [ ] **TRADE-02**: User can sell shares they own at the current price
- [ ] **TRADE-03**: User sees why a trade was rejected (invalid quantity, not enough cash or shares, no price)
- [ ] **TRADE-04**: Every executed trade is recorded in a trade history log

### Portfolio

- [ ] **PORT-01**: User can see total value and cash in the header, updating live
- [ ] **PORT-02**: User can see a positions table: quantity, average cost, price, unrealised P&L, % change
- [ ] **PORT-03**: User can see a heatmap of positions sized by weight and coloured by P&L
- [ ] **PORT-04**: User can see a chart of total portfolio value over time, recorded every 30 seconds and after each trade

### AI Chat

- [ ] **CHAT-01**: User can ask about their portfolio and get a concise answer based on current holdings and prices
- [ ] **CHAT-02**: User can ask the assistant to buy or sell, and approved trades execute without a confirmation step
- [ ] **CHAT-03**: User can ask the assistant to add or remove watchlist tickers
- [ ] **CHAT-04**: Proposed actions are checked by code, then by a second model that can only approve or reject; no trade executes if the review fails
- [ ] **CHAT-05**: User sees executed and rejected actions inline, with reasons
- [ ] **CHAT-06**: User sees conversation history and a loading indicator in a collapsible side panel
- [ ] **CHAT-07**: User gets a clear message when the model call fails, returns bad output or has no API key
- [ ] **CHAT-08**: Conversations are stored, and each call stays within the token budget (last 10 messages, compact context)
- [ ] **CHAT-09**: With `LLM_MOCK=true`, chat and review are deterministic and make no network calls

### Look and Feel

- [ ] **UI-01**: The app follows `planning/OUI_FORMAT.md`: logo, colours, fonts, components, header and footer
- [ ] **UI-02**: The layout is desktop-first and remains usable on tablet and phone widths
- [ ] **UI-03**: Direction and status are never shown by colour alone, and the app has AA contrast and visible focus

### Run and Ship

- [ ] **OPS-01**: One multi-stage Docker image runs the whole app on port 8000, with data kept on a volume
- [ ] **OPS-02**: User can start and stop it with idempotent macOS/Linux scripts
- [ ] **OPS-03**: Stopping the app completes cleanly even with price streams open

### Testing

- [ ] **TEST-01**: Backend unit tests cover portfolio and trade logic, LLM parsing and review, and API routes
- [ ] **TEST-02**: Frontend unit tests cover price flash, watchlist, portfolio calculations and chat
- [ ] **TEST-03**: Playwright tests cover the `planning/PLAN.md` section 12 scenarios against the container in mock mode

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Real Market Data

- **MKT-01**: The Massive data path works against the live service, with the open review findings fixed and a live smoke test

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Login and multi-user accounts | Single user today; the schema stays multi-user ready |
| Limit orders, order book, fees, partial fills | Market orders only keeps portfolio maths simple |
| Token-by-token chat streaming | A loading indicator is enough at Cerebras speed |
| Cloud deployment tooling | Not part of the core build |
| docker-compose | One container, one command |
| Windows `.ps1` scripts | Windows users can run the Docker commands or use WSL |
| Dark theme | openUI is a light theme |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|

**Coverage:**
- v1 requirements: 38 total
- Mapped to phases: 0
- Unmapped: 38 ⚠️

---
*Requirements defined: 2026-11-27*
*Last updated: 2026-11-27 after initial definition*
