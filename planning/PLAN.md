# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It is a data-dense, modern trading terminal with an AI copilot, styled in the openUI house style (see Section 2 and `planning/OUI_FORMAT.md`).

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/`.

## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A clean, data-dense trading terminal in the openUI style (light surfaces, teal/navy/orange palette)
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash teal (uptick) or orange (downtick), with an up/down arrow, using subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist, accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)
- **Click a ticker** to see a larger detailed chart in the main chart area
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

**All visual design follows the openUI format standard in `planning/OUI_FORMAT.md`.** It is the single source of truth for logo, colours, typography, components and layout; do not invent a separate palette. Where this plan and `OUI_FORMAT.md` disagree on visuals, `OUI_FORMAT.md` wins. The project foundation files already in the repo are:

| What | File |
|---|---|
| Design tokens and Tailwind utilities | `frontend/src/app/globals.css` |
| Shared components (Button, Panel, Eyebrow, TextField, Spinner, `cn`, `HEADING`, `SUBHEADING`) | `frontend/src/components/ui.tsx` |
| Logo component (use this, never a raw `<img>`) | `frontend/src/components/Logo.tsx` |
| Logo and favicon | `frontend/src/assets/openui-logo.png`, `frontend/src/app/icon.png` |

Fonts (Space Grotesk for headings, Manrope for body) are self-hosted via the Fontsource packages `@fontsource-variable/space-grotesk` and `@fontsource-variable/manrope`, imported in `layout.tsx`. Never load fonts from Google Fonts or a CDN.

Product-specific application of the standard:

- **Light theme**: page background `--surface` (`#f6f8f7`), content in white panels with the standard stroke and shadow. No dark theme and no pure black.
- **Header**: openUI logo (140 px) plus the product name "FinAlly" in the display font on the left; portfolio total value, cash balance and the connection indicator on the right. Header, content and footer share a max width of 1500 px with 24 px gutters.
- **Price flash animations**: on a price change, a brief background tint fading over ~500ms via CSS transitions. Uptick = teal-ink tint with an up arrow (▲); downtick = orange tint with a down arrow (▼). Direction is always shown by arrow and sign as well as colour.
- **P&L colouring** (positions table, heatmap, daily change %): profit = teal-ink text/fill with a `+` sign; loss = orange-ink with a `−` sign. Per openUI, never use red or green, and orange (non-ink) is never used for text.
- **Connection status indicator**: a small dot plus a text label: teal-ink = connected, orange = reconnecting, orange-ink = disconnected. Colour is never the only signal.
- **Charts**: series colours in the openUI order (teal-ink `#315f62`, orange `#d57e39`, navy `#263c3d`, orange-ink `#8f4a1b`, gray `#666666`); gridlines and axes `#e2e9e9`; labels gray.
- **Chat bubbles**: user = teal-ink with white text; assistant = surface with navy text. Trade and watchlist confirmations use the standard alert styling.
- **Buttons**: pill buttons from `ui.tsx`. Primary (teal-ink) for Buy and Send; Danger variant for Sell and Remove.
- **Data-dense layout**: dense tables and compact panels are fine, but the 4 px spacing grid, AA contrast, visible focus rings and phone-width usability from `OUI_FORMAT.md` still apply.
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet.
- **Page title** is "FinAlly | Trading Workstation" style (two to four words).

---

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, built as a static export (`output: 'export'`), served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, volume-mounted for persistence
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter (Cerebras for fast inference), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Multi-User Readiness (Design Constraint)

The product is single-user today, but the architecture must scale to multiple users without schema or API rewrites:

- **Every user-owned table keeps `user_id`** (see Section 7). Nothing in the schema assumes one user.
- **Identity is resolved in one place**: a single backend dependency (e.g. `get_current_user() -> str`) returns `"default"` today. Every route and service receives `user_id` from it; no code path hardcodes `"default"` outside that function and the seed data. Adding auth later means changing only this function.
- **Data-access functions always take `user_id`** as an explicit parameter and filter every query by it.
- **Market data is global, not per-user**: one price cache, one poller. The set of tickers to poll is the union of all users' watchlists and positions.
- **SSE price stream is shared** (all known tickers); per-user filtering happens client-side from that user's watchlist. Per-user events (if ever needed) are a separate stream.
- **Background tasks iterate over users** (e.g. portfolio snapshots loop over all user profiles) rather than assuming one.
- **SQLite is acceptable for now**; the data layer is isolated behind `backend/db/` so a move to Postgres only touches that module.

### Why These Choices

| Decision | Rationale |
|---|---|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity, universal browser support |
| Static Next.js export | Single origin, no CORS issues, one port, one container, simple deployment |
| SQLite over Postgres | No auth = no multi-user = no need for a database server; self-contained, zero config |
| Single Docker container | Students run one command; no docker-compose for production, no service orchestration |
| uv for Python | Fast, modern Python project management; reproducible lockfile; what students should learn |
| Market orders only | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project (static export)
├── backend/                  # FastAPI uv project (Python)
│   └── db/                   # Schema definitions, seed data, migration logic
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   └── stop_mac.sh           # Stop Docker container (macOS/Linux)
├── test/                     # Playwright E2E tests (run on the host against the container)
├── db/                       # Volume mount target (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/db/`** contains schema SQL definitions and seed logic. The backend lazily initializes the database on first request — creating tables and seeding default data if the SQLite file doesn't exist or is empty.
- **`db/`** at the top level is the runtime volume mount point. The SQLite file (`db/finally.db`) is created here by the backend and persists across container restarts via Docker volume.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests, which run on the host against the single app container. Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

## 5. Environment Variables

```bash
# Required: OpenRouter API key for LLM chat functionality
OPENROUTER_API_KEY=your-openrouter-api-key-here

# Optional: Massive (Polygon.io) API key for real market data
# If not set, the built-in market simulator is used (recommended for most users)
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing)
LLM_MOCK=false
```

### Behavior

- If `MASSIVE_API_KEY` is set and non-empty → backend uses Massive REST API for market data
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` → backend returns deterministic mock LLM responses (for E2E tests)
- The backend reads `.env` from the project root (mounted into the container or read via docker `--env-file`)

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves across tickers (e.g., tech stocks move together)
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Runs as an in-process background task — no external dependencies

### Massive API (Optional)

- REST API polling (not WebSocket) — simpler, works on all tiers
- Polls for the union of all watched tickers on a configurable interval
- Free tier (5 calls/min): poll every 15 seconds
- Paid tiers: poll every 2-15 seconds depending on tier
- Parses REST response into the same format as the simulator

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds the latest price, previous price, and timestamp for each ticker
- SSE streams read from this cache and push updates to connected clients
- This architecture supports future multi-user scenarios without changes to the data layer

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- Server pushes price updates for all tickers known to the system at a regular cadence (~500ms) — in the single-user model this is equivalent to the user's watchlist
- Each SSE event contains ticker, price, previous price, timestamp, and change direction
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### SQLite with Lazy Initialization

The backend checks for the SQLite database on startup (or first request). If the file doesn't exist or tables are missing, it creates the schema and seeds default data. This means:

- No separate migration step
- No manual database setup
- Fresh Docker volumes start with a clean, seeded database automatically

### Schema

All user-owned tables include a `user_id` column defaulting to `"default"`. Only one user exists today, but the column is **deliberately kept** so multi-user support needs no schema migration (see "Multi-User Readiness" in Section 3). Add indexes on `user_id` (and `(user_id, recorded_at)` / `(user_id, created_at)` for snapshots and chat) so per-user queries stay fast as users grow. `users_profile` remains a real table, one row per user.

**users_profile** — User state (cash balance)
- `id` TEXT PRIMARY KEY (default: `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings (one row per ticker per user)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL (fractional shares supported)
- `avg_cost` REAL
- `updated_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**trades** — Trade history (append-only log)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL (fractional shares supported)
- `price` REAL
- `executed_at` TEXT (ISO timestamp)

**portfolio_snapshots** — Portfolio value over time (for P&L chart). Recorded every 30 seconds by a background task, and immediately after each trade execution.
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**chat_messages** — Conversation history with LLM
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. API Endpoints

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE stream of live price updates |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current positions, cash balance, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | Execute a trade: `{ticker, quantity, side}` |
| GET | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart) |

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | Current watchlist tickers with latest prices |
| POST | `/api/watchlist` | Add a ticker: `{ticker}` |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message, receive complete JSON response (message + executed actions) |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (for Docker/deployment) |

---

## 9. LLM Integration

When writing code to make calls to LLMs, use cerebras-inference skill to use LiteLLM via OpenRouter to the `openrouter/openai/gpt-oss-120b` model with Cerebras as the inference provider. Structured Outputs should be used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads recent conversation history from the `chat_messages` table
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter, requesting structured output, using the cerebras-inference skill
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response
7. Stores the message and executed actions in `chat_messages`
8. Returns the complete JSON response to the frontend (no token-by-token streaming — Cerebras inference is fast enough that a loading indicator is sufficient)

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"}
  ]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells)
- `watchlist_changes` (optional): Array of watchlist modifications

### Second-Opinion Review (Checks and Balances)

Trades and watchlist changes proposed by the primary LLM are **not executed directly**. A second, independent LLM call acts as a reviewer, so no single model output can move money on its own.

Flow:

1. **Proposer** (primary LLM, as above) returns `message`, `trades`, `watchlist_changes`.
2. **Deterministic validation** (code, no LLM): ticker known, quantity > 0, sufficient cash / shares. Failures are rejected immediately with a reason.
3. **Reviewer** (second LLM call, same model family is fine but a fresh context and a different system prompt) receives the portfolio context, the user's message, and the surviving proposed actions. It returns a structured verdict per action.
4. **Execute** only actions that passed steps 2 and 3, through the same trade/watchlist service used by the REST endpoints.
5. **Report**: the final chat response lists executed actions and any rejected ones with reasons.

Reviewer structured output:

```json
{
  "reviews": [
    {"action_index": 0, "type": "trade", "verdict": "approve", "reason": "Matches the user's explicit request; within cash."},
    {"action_index": 1, "type": "trade", "verdict": "reject", "reason": "Would put 80% of portfolio in one ticker; user did not ask for this."}
  ],
  "summary": "Optional note appended to the assistant message"
}
```

Reviewer rules:
- It can only **approve or reject** proposed actions. It cannot add, modify or resize them.
- It checks: the action is consistent with what the user actually asked for or agreed to (guards against the proposer inventing trades), the sizing is not wildly out of proportion to the portfolio, and there is no concentration or obvious-error risk (wrong ticker, wrong side, quantity typo such as 1000 instead of 10).
- If the proposer returns no actions, the reviewer call is skipped (no extra latency or cost for pure conversation).
- **Fail closed**: if the reviewer call times out, errors, or returns malformed output, no trades execute and the user is told the review failed. Watchlist-only changes may be set to fail open (low risk) — decide during implementation.
- Both verdicts and reasons are stored in `chat_messages.actions` for auditability.
- In `LLM_MOCK=true` mode the reviewer is also mocked deterministically (approve all by default; a trigger phrase can force a rejection for E2E tests).

### Token & Integration Budget

Keep LLM cost and latency low and the integration surface minimal:

- **Only essential external services**: OpenRouter (LLM, routed to Cerebras) is the only required third party. Massive is opt-in via `MASSIVE_API_KEY`. No analytics, auth providers, hosted databases, or font/CDN dependencies; all assets are bundled in the image.
- **History cap**: send at most the last 10 messages (5 exchanges) from `chat_messages` to the proposer. Older messages stay in the database but are not sent.
- **Compact context**: portfolio context is a terse JSON/table (cash, total value, and per position: ticker, qty, avg cost, price, P&L %; watchlist as `ticker:price`). No verbose prose, no sparkline or history data.
- **Stable prompt prefix**: put the static system prompt and schema instructions first and the dynamic portfolio data and user message last, so provider-side prompt caching can apply where available.
- **Proposer limits**: set `max_tokens` (e.g. 800) and low reasoning effort on `gpt-oss-120b`. Instruct it to keep `message` to a few sentences.
- **Reviewer gets minimum context**: only the user's latest message, the proposed actions, and cash plus positions. No conversation history and no watchlist. Set a small `max_tokens` (e.g. 300), low reasoning effort, and one-sentence reasons.
- **Skip calls when pointless**: no reviewer call when there are no actions; deterministic validation runs first so obviously invalid actions never reach the reviewer.
- **Mock mode** makes zero network calls.

### Auto-Execution

Trades specified by the LLM execute automatically once they pass validation and the reviewer — no user confirmation dialog. This is a deliberate design choice:
- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

If a trade fails validation or is rejected by the reviewer (e.g., insufficient cash), the reason is included in the chat response. The backend appends rejection reasons to the assistant message; no third LLM call is needed.

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:
- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-style layout in the openUI style. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing teal/orange with ▲/▼ on change), daily change %, and a sparkline mini-chart (accumulated from SSE since page load)
- **Main chart area** — larger chart for the currently selected ticker, with at minimum price over time. Clicking a ticker in the watchlist selects it here.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (teal-ink = profit, orange-ink = loss, with +/− signs; see Section 2)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — simple input area: ticker field, quantity field, buy button, sell button. Market orders, instant fill.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, loading indicator while waiting for LLM response. Trade executions and watchlist changes shown inline as confirmations.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- Use **Recharts** as the single charting library for everything: price chart, sparklines, P&L line chart and the portfolio treemap. One dependency, no second library; at ~10 tickers SVG rendering performance is fine
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS v4 for styling, using the openUI tokens in `frontend/src/app/globals.css` and the components in `frontend/src/components/ui.tsx` (no raw hex values; no separate theme)
- Frontend scaffolding (`create-next-app` or equivalent) must **preserve** the existing files under `frontend/src/` (`app/globals.css`, `app/icon.png`, `assets/openui-logo.png`, `components/Logo.tsx`, `components/ui.tsx`)
- Header and footer components (`SiteHeader`, `SiteFooter`) are built for FinAlly following `OUI_FORMAT.md` Section 4; the Prelegal versions are not reused (they depend on Prelegal auth)

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - npm install && npm run build (produces static export)

Stage 2: Python 3.12 slim
  - Install uv
  - Copy backend/
  - uv sync (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

FastAPI serves the static frontend files and all API routes on port 8000.

### Docker Volume

The SQLite database persists via a named Docker volume:

```bash
docker run -v finally-data:/app/db -p 8000:8000 --env-file .env finally
```

The `db/` directory in the project root maps to `/app/db` in the container. The backend writes `finally.db` to this path.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):
- Builds the Docker image if not already built (or if `--build` flag passed)
- Runs the container with the volume mount, port mapping, and `.env` file
- Prints the URL to access the app
- Optionally opens the browser

**`scripts/stop_mac.sh`** (macOS/Linux):
- Stops and removes the running container
- Does NOT remove the volume (data persists)

Windows users can run the equivalent `docker` commands shown above directly (or via WSL); no PowerShell scripts are provided in the core build.

All scripts should be idempotent — safe to run multiple times.

### Cloud Deployment

Out of scope for the core build. The container is a standard single-port image and can be run on any container platform, but no cloud-specific tooling (Terraform, App Runner config) is part of this project.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:
- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:
- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and loading state

### E2E Tests (in `test/`)

**Infrastructure**: Playwright is installed in `test/` and runs on the host against the single app container (started with the normal start script and `LLM_MOCK=true`). No second container or compose file; browser dependencies stay out of the production image.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**Key Scenarios**:
- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: heatmap renders with correct colors, P&L chart has data points
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- SSE resilience: disconnect and verify reconnection

---

## 13. Review: Questions, Clarifications & Simplifications

*Added by doc-review. Feedback for the plan owner; nothing above has been changed.*

### Questions / ambiguities

1. **Trade validation rules**: Is a ticker missing from the price cache rejected? Can the user trade a ticker that is not on the watchlist? Are minimum sizes and fractional precision defined? Does a sell to exactly 0 delete the position row?
2. **Watchlist removal with an open position**: Does removing the ticker stop it streaming? The positions table and P&L still need its price. Define "tickers known to the system" as the union of watchlist and positions.
3. **Adding arbitrary tickers**: The simulator needs seed prices and parameters for unknown tickers (e.g. PYPL in the chat example). What price does a new ticker start at? With Massive, how is an invalid ticker detected?
4. **"Daily change %"**: The cache holds only latest and previous price. What is the baseline: session open, previous close (Massive), or the first simulator price?
5. **Error response shape**: Define a standard error JSON for 4xx responses on trade and watchlist routes. The chat flow needs it to report failed trades.
6. **Chat failure handling**: What happens on a malformed LLM response, a timeout, or a missing `OPENROUTER_API_KEY`? Is there a retry? How many history messages are sent?
7. **Trade failure semantics in chat**: Does one failed trade abort the rest, or does each execute independently? Does the LLM get a second pass to explain failures, or does the backend append the errors? (Section 9 says "so the LLM can inform the user", which implies a second call.)
8. **Portfolio snapshots**: The 30s task writes forever, so the table grows unbounded. Add a retention or downsampling rule, and say whether `/api/portfolio/history` is capped.
9. **Massive and closed markets**: Prices will not change when markets are closed, and the free tier allows 5 calls/min. Confirm the polling design stays within that rate.
10. **Docker / .env**: The plan says the backend reads `.env` from the project root, but the container only gets it via `--env-file`. Pick one. Also clarify named volume vs bind mount (`finally-data` vs `./db`).
11. **Static serving**: API routes must be registered before the static mount. Confirm the frontend is a single page with no client-side routing.
12. **Testing**: Which frontend test runner (Jest or Vitest)? Is Playwright E2E required for the first milestone?

### Clarifications to add to the spec

- Define the JSON contract for the SSE event and for `/api/portfolio` and `/api/watchlist` responses. Frontend and backend agents need it as a shared contract.
- State the rounding rule for prices (e.g. 2 decimals) and the cash check (e.g. `cost <= cash`).
- State float vs Decimal for money. REAL columns can drift; that is acceptable for a simulation, but say so.
- Specify start-script behavior when port 8000 is busy and whether the browser opens automatically.
- Note how the Cerebras provider is pinned for `openrouter/openai/gpt-oss-120b` (via the cerebras-inference skill).
- Accessibility: ~~red/green is the only P&L signal~~ **Addressed**: openUI palette (teal-ink / orange-ink) plus ▲/▼ arrows and +/− signs; see Section 2.

### Simplification opportunities

1. ~~**Drop `user_id` columns**~~ **Rejected**: multi-user scalability is a requirement. `user_id` is kept and the design constraint is documented in Section 3.
2. ~~**Replace `users_profile`**~~ **Rejected** for the same reason; `users_profile` stays one row per user.
3. **One snapshot mechanism**: The 30s background task plus after-trade writes is two mechanisms. Consider a single timer, or snapshot only on trades plus a slower timer.
4. ~~**Skip the second LLM pass**~~ **Rejected**: a second LLM now acts as reviewer for checks and balances (Section 9). Rejection reasons are still appended server-side, so no third call is needed.
5. ~~**Remove `docker-compose.yml` and the Terraform stretch goal**~~ **Applied.**
6. ~~**Lighter E2E setup**~~ **Applied**: Playwright runs on the host.
7. ~~**Pick one charting library**~~ **Applied**: Recharts for all charts and the treemap.
8. **Keep SSE simple**: Send all tickers every ~500ms. With about 10 tickers, diffing is not worth it.
9. ~~**Defer Windows `.ps1` scripts**~~ **Applied.**
10. **Initialize the DB at startup** (FastAPI lifespan) rather than "startup or first request", which removes a code path.

### Suggested build order

Backend core (DB, portfolio, watchlist, API contracts) → SSE wiring → LLM chat with mock mode → frontend → Docker and scripts → E2E.
