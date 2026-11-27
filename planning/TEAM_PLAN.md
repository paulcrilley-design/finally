# FinAlly — Agent Team Plan

**Status (2026-11-27):** complete. All stages are built, committed and pushed to `agent-teams`
(not merged to `main`). Passing: 225 backend, 23 frontend and 23 Playwright tests.

**Goal:** build the rest of the platform as defined in `PLAN.md` using an agent team. Market data
is already built (`MARKET_DATA_SUMMARY.md`). Work on branch `agent-teams`.

## Team (the main session is lead and coordinator)

All teammates run on **Sonnet**. Each engineer writes unit tests for their own code. Each file area
has one owner, because teammates share one working folder.

| Teammate | Owns | Delivers |
|---|---|---|
| Database Engineer | `backend/db/` | Schema, seed data, lazy initialisation, data access by `user_id` |
| Backend API Engineer | `backend/app/` except `llm/` | FastAPI app, portfolio, trade and watchlist routes, snapshots, SSE wiring, static serving |
| LLM Engineer | `backend/app/llm/` | `/api/chat`, proposer and reviewer calls (`cerebras` skill), structured outputs, mock mode |
| Front-End Engineer | `frontend/` | Next.js static export, all panels, charts, openUI styling (`OUI_FORMAT.md`) |
| DevOps Engineer | `Dockerfile`, `.dockerignore`, `scripts/` | Image, start and stop scripts, health check |
| Integration Tester | `test/` | Playwright tests against the container, bug reports to the owner |

## Order (staged, to limit token use)

1. **Contracts (lead):** write `planning/CONTRACTS.md` with API and SSE event JSON shapes, error
   format, database and service function signatures, shared files and their owner (for example
   `backend/pyproject.toml`), and test selectors.
2. **Stage A:** Database, Backend API and LLM engineers.
3. **Stage B:** Front-End engineer.
4. **Stage C:** DevOps engineer, then Integration Tester. Tests run with `LLM_MOCK=true`. Owners fix
   reported bugs until the tests pass.
5. **Finish (lead):** full check, update the README, commit and push to `agent-teams`.
   Do not merge to `main`.

Token rules: teammates read `CONTRACTS.md` and only the parts of `PLAN.md` they need. Retire a
teammate when finished and bring them back only for bugs in their area. Between stages, ask Paul to
check `/usage`; pause at 80% of the 5-hour limit and update the status line above.

## Decisions on the open questions in PLAN.md Section 13

- **Trades:** a ticker with no live price is rejected. Off-watchlist trades are allowed if priced.
  Fractions to 4 decimals. Selling to zero removes the position.
- **Chat:** trades execute independently. Any failure of the proposer call returns a clear message
  with no actions. A failed review blocks trades and watchlist changes.
- **History:** snapshots kept for 7 days; the history endpoint returns at most 500 points.
- **Docker:** `.env` passed with `--env-file`; named volume `finally-data`.
- **Tooling:** Vitest for frontend unit tests. `MASSIVE_API_KEY` stays empty (that path is not ready).

## What approval covers

Installing packages, Docker builds, starting the app, and a few small live OpenRouter calls to check
the chat. Docker Desktop must be running before Stage C.
