# Review of `planning/PLAN.md`

## Overall assessment

The plan is coherent, appropriately scoped for a capstone, and strong enough to begin implementation. Its best qualities are the single-container constraint, explicit design-system ownership, shared market-data abstraction, deterministic LLM mock mode, and clear separation between deterministic trade validation and LLM judgment.

I recommend **proceeding after a short contract-and-integrity pass**. The main risk is not the architecture; it is that several backend/frontend boundaries and transaction rules remain open to interpretation. Those gaps could produce components that work independently but do not integrate safely.

## Findings

### P0 — Resolve before parallel frontend/backend work

1. **The documented SSE contract conflicts with the completed implementation.**

   Section 6 describes each event as one ticker update. The implemented stream sends a map keyed by ticker, containing all cached prices, and emits only when the cache version changes. Choose that implemented shape as the contract and show an exact JSON example in the plan. Also define timestamp units and numeric types. Add a periodic SSE comment/heartbeat because the Massive source may produce no cache changes for long periods when markets are closed.

2. **Trade execution needs an explicit atomicity and concurrency contract.**

   Cash/share validation, position mutation, cash mutation, trade-log insertion, and the after-trade snapshot must occur in one SQLite transaction. Otherwise two simultaneous manual/chat requests can both pass validation and overspend cash or oversell shares. Specify transaction locking/retry behavior (for example, `BEGIN IMMEDIATE` with a short busy timeout), rollback semantics, and whether a batch of LLM actions is atomic or independently committed.

3. **API response contracts are still missing.**

   Section 8 lists routes but not request/response models. Add canonical examples or schemas for portfolio, history, watchlist, trade success, chat success, and errors. Include status codes, field names, nullability, timestamp format, price precision, and the executed/rejected action shape. This is the key shared contract for independently implemented frontend and backend code.

4. **Ticker lifecycle must be defined as reference reconciliation, not simple add/remove.**

   The active market-data set must be the union of every user's watchlist and open positions. Removing a ticker from a watchlist must not call `source.remove_ticker()` while any position or another user still references it. Define one reconciliation service that computes additions/removals after watchlist or position changes and on startup. Also decide how unknown simulator tickers and invalid Massive symbols are handled.

### P1 — Resolve while implementing the backend

5. **Money and quantity rules need deterministic definitions.**

   State whether calculations use integer cents/`Decimal` or SQLite `REAL`, where rounding occurs, allowed fractional-share precision, minimum quantity, treatment of dust, and whether selling the full quantity deletes the position. Add database `CHECK` constraints for positive quantities/prices, valid sides/roles, and non-negative cash where applicable. Add foreign keys to `users_profile` and enable SQLite foreign-key enforcement.

6. **Retries can duplicate mutating actions.**

   A browser retry, double click, or repeated chat submission can execute a trade twice. Add a client-generated idempotency key to manual trade and chat requests, persist it with an appropriate uniqueness scope, and return the prior result on replay. Disable buttons while a request is pending as a UI safeguard, but do not rely on that for correctness.

7. **The LLM action/review protocol has unresolved semantics.**

   Define whether `action_index` is global across trades and watchlist changes or local to each type. Make reviewer output require exactly one verdict for every surviving action and reject the whole review response if indexes are missing, duplicated, or unknown. Decide the currently open fail-open/fail-closed rule for watchlist changes. Clarify that actions execute independently or as a batch, and that validation is repeated inside the execution transaction because portfolio state may change during the LLM calls.

8. **The review policy and system-prompt guidance pull in different directions.**

   The assistant is told to manage the watchlist “proactively,” while the reviewer approves actions consistent with what the user asked for or agreed to. Pick one policy. A safe, predictable rule is: analysis and suggestions may be proactive, but mutations require explicit user intent in the current or clearly referenced recent turn.

9. **“Daily change” cannot be derived from the specified cache.**

   Latest price and previous tick only provide tick-to-tick change. Define a baseline field—previous close for Massive and session-start price for the simulator—or rename the UI value to session change. Put the baseline and calculated percentage in one authoritative layer to avoid frontend/backend disagreement.

10. **Portfolio-history growth and meaning need bounds.**

    Define retention, response limits, ordering, and time range for `/api/portfolio/history`. State whether the chart shows total-value history or P&L relative to the initial/deposit-adjusted baseline. With no deposits today these can look similar, but they are not the same contract.

### P2 — Documentation and delivery cleanup

11. **The persistence description contradicts the Docker command.**

    The command uses a named volume (`finally-data:/app/db`), but the next sentence says the repository's `db/` directory maps to `/app/db`, which would require a bind mount such as `./db:/app/db`. Select one. A named volume is simpler, but then the top-level `db/` directory is not the runtime mount target.

12. **Database initialization is described three ways.**

    The plan says “lazily,” “on startup (or first request),” and later recommends startup initialization. Use the FastAPI lifespan exclusively. Initialization and seeding should be idempotent and complete before the health endpoint reports ready.

13. **The no-key first-launch experience is unclear.**

    The vision promises immediate use, while `OPENROUTER_API_KEY` is required. Specify that the trading workstation remains usable without a key and that chat displays a clear unavailable/configuration state, or make mock mode the no-key development fallback. Do not silently make network calls in mock mode.

14. **Operational details should be made reproducible.**

    Pin the model/provider routing in code/config rather than depending on an agent skill at runtime. Add the missing backend dependency plan for LiteLLM and SQLite access. In Docker, prefer lockfile-enforced installs (`npm ci` and frozen `uv sync`) and add a container health check. Define the start script's behavior for a missing `.env`, a busy port, an existing stopped/running container, and browser opening.

15. **The testing section needs a few high-risk cases.**

    Add concurrent buy/sell tests, idempotency replay, SQLite restart/persistence, atomic rollback, open-position watchlist removal, invalid/unknown ticker handling, LLM reviewer malformed/missing/duplicate verdicts, provider timeout, SSE heartbeat/reconnect, and a production static-export smoke test. The E2E suite should reset or isolate database state so test order cannot change results.

## Recommended decisions

- Treat the existing batched SSE payload as canonical and document it.
- Use FastAPI lifespan for schema setup, seed data, market-source startup, snapshot task startup, and orderly shutdown.
- Centralize all trade execution—REST and chat—in one transactional service.
- Use one ticker-reconciliation service for the watchlist/positions union.
- Make chat and trade POST requests idempotent.
- Use explicit user intent for all AI-triggered mutations; allow proactive suggestions only.
- Keep the second-opinion reviewer, but describe it as an additional model check rather than full independence when it uses the same model/provider.

## Strengths worth preserving

- Clear product vision and deliberately constrained first release.
- Excellent mock-mode requirement for deterministic, network-free tests.
- Good separation of market source, price cache, streaming, and downstream consumers.
- Strong visual-system guidance and accessibility signals beyond color alone.
- Practical single-port deployment and host-run Playwright setup.
- Sensible cap on chat history and reviewer context.
- Multi-user-aware schema and service signatures without prematurely adding authentication.

## Suggested next step

Add a compact “normative contracts” appendix to `PLAN.md` containing the API/SSE schemas, transaction and idempotency rules, ticker lifecycle, numeric rules, and error codes. Once that appendix is agreed, the existing suggested build order is sound.
