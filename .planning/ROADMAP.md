# Roadmap: FinAlly

## Overview

Only the market data subsystem exists today. Five vertical slices turn it into the finished trading workstation: first a running terminal with live prices, then trading with correct portfolio numbers, then charts, then the AI copilot with its second-model review, and finally a one-command Docker run proven end to end. The order follows the core value (the trading terminal works) ahead of the copilot and release polish.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Live Market Terminal** - Open the app in a browser and watch the default watchlist stream live prices
- [ ] **Phase 2: Trading and Positions** - Buy and sell at market price, manage the watchlist, and see correct cash, positions and P&L
- [ ] **Phase 3: Price and Portfolio Charts** - Sparklines, ticker chart, portfolio heatmap and value-over-time chart
- [ ] **Phase 4: AI Copilot** - Chat that analyses the portfolio and executes reviewed trades and watchlist changes
- [ ] **Phase 5: One-Command Run and Release** - One script starts the container, data persists, layout adapts and all tests pass

**Testing across phases:** every phase writes unit tests for what it builds. TEST-01 and TEST-02 are closed in Phase 5, once the logic they cover all exists.

## Phase Details

### Phase 1: Live Market Terminal
**Goal:** As a trader, I want to open the app and watch prices stream live, so that I can follow the market at a glance.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: APP-01, APP-02, APP-03, APP-05, WATCH-01, WATCH-02, WATCH-07, UI-01, UI-03, OPS-03
**Success Criteria** (what must be TRUE):
  1. User opens `http://localhost:8000` with no login and sees the FinAlly terminal (openUI logo, colours, self-hosted fonts, components, header and footer), with the pages and API served by one process
  2. A start with no database file creates one holding $10,000 cash and the 10 default tickers, which appear in the watchlist; every user-owned table carries `user_id`, supplied by a single identity function
  3. User sees each ticker's price and daily change % update live, with a fading flash and ▲/▼ on each price change; direction and status read without colour, text meets AA contrast and keyboard focus is visible
  4. A dot with a text label shows connected, reconnecting or disconnected, and after a server restart the prices resume without reloading the page
  5. The health endpoint reports whether the app and market data are working, and stopping the server with the page still open completes cleanly

**Decide in discussion**: frontend test runner; database setup at startup or first request; `.env` loading; SSE and watchlist response contracts
**Notes**: Write the frontend fresh to `planning/OUI_FORMAT.md` (the old design files stay deleted); copy the logo and `Logo.tsx` with `standards/sync-brand.sh`. Run uvicorn with `--timeout-graceful-shutdown 3`. Leave `MASSIVE_API_KEY` empty
**Plans**: 11 plans

Plans:
**Wave 1**
- [ ] 01-01-PLAN.md — Owner approval of the flagged packages and ignore rules before any install (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 01-02-PLAN.md — Walking skeleton tracer: seeded database to live prices on the served page (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [ ] 01-11-PLAN.md — Stored watchlist API, single identity and watchlist order on the page (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [ ] 01-03-PLAN.md — Data guarantees under test, env loading and the run command (wave 4)
- [ ] 01-04-PLAN.md — Frontend tests and lint around the live page (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [ ] 01-05-PLAN.md — Health endpoint and clean shutdown with a stream open (wave 5)
- [ ] 01-06-PLAN.md — openUI colours, fonts and the watchlist in its own modules (wave 5)

**Wave 6** *(blocked on Wave 5 completion)*
- [ ] 01-07-PLAN.md — Daily change, price flash and arrow (wave 6)
- [ ] 01-08-PLAN.md — openUI brand files, shared components, header and footer (wave 6)

**Wave 7** *(blocked on Wave 6 completion)*
- [ ] 01-09-PLAN.md — Connection status and reconnect (wave 7)

**Wave 8** *(blocked on Wave 7 completion)*
- [ ] 01-10-PLAN.md — openUI page layout, accessibility, README and end-of-phase checks (wave 8)

**UI hint**: yes

### Phase 2: Trading and Positions
**Goal:** As a trader, I want to trade and manage my watchlist, so that I can run my virtual portfolio and trust its numbers.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: TRADE-01, TRADE-02, TRADE-03, TRADE-04, PORT-01, PORT-02, WATCH-05, WATCH-06
**Success Criteria** (what must be TRUE):
  1. User can buy a ticker, including a fraction of a share, from the trade bar; it fills at the current price, cash falls by quantity times price and the position appears
  2. User can sell shares they own; cash rises and the position shrinks, or disappears when all are sold, and every executed buy and sell is recorded in the trade history log
  3. A trade with an invalid quantity, not enough cash or shares, or no current price is refused with the reason shown, and cash, positions and history stay unchanged
  4. The header's total value and cash and the positions table (quantity, average cost, price, unrealised P&L, % change) update live and agree with each other
  5. User can add a ticker and see it start streaming, and can remove one; a removed ticker with an open position keeps being priced in the positions table and total value

**Decide in discussion**: trade validation, precision and rounding rules; standard error response shape; portfolio and watchlist API contracts; how to handle the P&L jump when simulator prices reset on restart
**Notes**: Call `normalize_ticker()` before any cache lookup, reject a trade with no price, and call `reconcile_tickers` after watchlist or trade changes
**Plans**: TBD
**UI hint**: yes

### Phase 3: Price and Portfolio Charts
**Goal:** As a trader, I want to chart prices and my portfolio, so that I can see trends and where my money is at risk.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: WATCH-03, WATCH-04, PORT-03, PORT-04
**Success Criteria** (what must be TRUE):
  1. Each watchlist row shows a sparkline that starts empty on page load and fills in as prices arrive
  2. User clicks a ticker and sees its larger price chart in the main chart area, updating live; clicking another ticker switches the chart
  3. The heatmap shows one rectangle per position, sized by portfolio weight and coloured by P&L (teal-ink with `+`, orange-ink with `−`), and follows price moves and new trades
  4. The portfolio value chart gains a point every 30 seconds and immediately after each trade, and earlier points are still shown after a page reload

**Decide in discussion**: snapshot retention or downsampling, and any cap on the history endpoint
**Notes**: Recharts is the only charting library, including the treemap
**Plans**: TBD
**UI hint**: yes

### Phase 4: AI Copilot
**Goal:** As a trader, I want to chat with an AI that analyses and trades safely, so that I can act in plain English.
**Mode:** mvp
**Depends on**: Phase 2 (trade and watchlist services)
**Requirements**: CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, CHAT-08, CHAT-09
**Success Criteria** (what must be TRUE):
  1. User asks about their portfolio in a collapsible side panel, sees a loading indicator and then a concise answer based on current holdings and prices, and the conversation history is still there after a reload
  2. User asks the assistant to buy, sell, or add or remove a watchlist ticker; approved actions happen with no confirmation step and cash, positions and watchlist update on screen
  3. Every proposed action is checked by code and then by a second model that can only approve or reject; if the review times out, errors or returns bad output, no trade executes and the user is told
  4. Executed and rejected actions appear inline with reasons, and a failed model call, bad output or missing API key shows a clear message while the rest of the terminal keeps working
  5. With `LLM_MOCK=true` the same message always gives the same reply and verdict (including a forced rejection) with no network calls; every live call stays within the last 10 messages and compact context

**Decide in discussion**: retry and timeout handling; whether one failed action stops the rest; whether watchlist-only changes fail open when review fails
**Notes**: Use the `cerebras` skill (LiteLLM, OpenRouter, `openrouter/openai/gpt-oss-120b`, structured outputs). Execute actions through the same services as the REST routes
**Plans**: TBD
**UI hint**: yes

### Phase 5: One-Command Run and Release
**Goal:** As a trader, I want to start the finished app with one command, so that it runs reliably and keeps my data.
**Mode:** mvp
**Depends on**: Phase 3, Phase 4
**Requirements**: OPS-01, OPS-02, APP-04, UI-02, TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. User runs the macOS/Linux start script and gets the whole app on `http://localhost:8000` from one multi-stage Docker image; the stop script shuts it down, and running either script twice is harmless
  2. After stopping and starting the container, cash, positions, watchlist, trade history and chat are as the user left them, held on a volume
  3. Every panel is usable at tablet and phone widths with no horizontal page scroll, while the wide desktop layout stays primary
  4. Backend and frontend unit test suites pass and cover portfolio and trade logic, LLM parsing and review, API routes, price flash, watchlist, portfolio calculations and chat
  5. Playwright tests run from the host against the container in mock mode pass every `planning/PLAN.md` section 12 scenario, including stream reconnection

**Decide in discussion**: how the container gets `.env`; named volume or bind mount; start-script behaviour when port 8000 is busy and whether it opens the browser
**Notes**: `test/` has no `package.json`, so the Playwright setup starts fresh
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Live Market Terminal | 0/TBD | Not started | - |
| 2. Trading and Positions | 0/TBD | Not started | - |
| 3. Price and Portfolio Charts | 0/TBD | Not started | - |
| 4. AI Copilot | 0/TBD | Not started | - |
| 5. One-Command Run and Release | 0/TBD | Not started | - |
