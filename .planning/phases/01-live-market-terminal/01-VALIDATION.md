---
phase: "1"
slug: "live-market-terminal"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-27"
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 (backend, installed); Vitest (frontend, Wave 0 installs) |
| **Config file** | `backend/pyproject.toml`; `frontend/vitest.config.mts` (Wave 0) |
| **Quick run command** | `cd backend && uv run --extra dev pytest tests/test_api.py -x -q` or `cd frontend && npx vitest run src/lib` |
| **Full suite command** | `cd backend && uv run --extra dev pytest -q && uv run --extra dev ruff check .` and `cd frontend && npm run test:unit && npm run lint && npm run typecheck` |
| **Estimated runtime** | not yet measured |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the side touched (before plan 01-04 adds Vitest, the frontend check is `npm --prefix frontend run typecheck`)
- **After every plan wave:** Run the full suite on both sides
- **Before `/gsd-verify-work`:** Full suite green, then the manual checks
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Task IDs are filled in from the plans. The requirement-to-test map is below.

| Req ID | Behaviour | Type | Automated Command | File Exists? | Plans |
|--------|-----------|------|-------------------|--------------|-------|
| APP-01 | `/` serves index, API wins over static, unknown `/api` is JSON 404 | integration | `uv run --extra dev pytest tests/test_api.py -x` | No, Wave 0 | 01-02 |
| APP-02 | Health shape; degraded on degraded or stale source | integration | same file | No | 01-05 |
| APP-03 | Fresh file gets 6 tables, cash 10000.0, 10 tickers in order; second init changes nothing, removed ticker stays removed | unit | `uv run --extra dev pytest tests/test_db.py -x` | No | 01-02, 01-03 |
| APP-05 | Owned tables have `user_id`; overriding `get_current_user` yields an empty watchlist | unit and integration | both files | No | 01-02, 01-03 |
| WATCH-01 | Watchlist order, null price fields; table renders price, change %, "—" | integration and component | pytest; `npx vitest run src/app src/components/Watchlist.test.tsx` | No | 01-02, 01-04, 01-07 |
| WATCH-02 | Reducer cases (first, repeat timestamp, unchanged price, up, down); arrow and class rendered | unit and component | `npx vitest run src/lib/ticks.test.ts` | No | 01-07 |
| WATCH-07 | open, error, 10 s, errors after 10 s stay disconnected, CLOSED recreate, cleanup | unit (fake timers) | `npx vitest run src/lib/priceStream.test.ts` | No | 01-09 |
| UI-01 | Header logo alt "openUI", "FinAlly", footer text; fonts self-hosted | component, plus manual look | `npx vitest run src/components` | No | 01-06, 01-08, 01-10 |
| UI-03 | Visible status text and screen-reader direction text; contrast and focus | component, plus manual | same | No | 01-07, 01-09, 01-10 |
| OPS-03 | Real uvicorn with open stream exits and runs lifespan shutdown | integration | `uv run --extra dev pytest tests/test_shutdown.py -x` | No | 01-05, 01-10 |

---

## Wave 0 Requirements

- [ ] `.gitignore` fix (01-02) and `db/.gitkeep` (01-03)
- [ ] `backend/tests/test_api.py` (01-02), `test_db.py` (01-03), `test_shutdown.py` (01-05), with app fixtures (temp DB, temp static dir, simulator forced)
- [ ] `frontend/` toolchain (01-02); `vitest.config.mts`, `src/test/setup.ts`, `src/test/fakeEventSource.ts` (01-04)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Appearance, price flash, keyboard focus, phone width | UI-01, UI-03, WATCH-02 | Visual judgement | Build, run the documented command, inspect in a browser |
| Connection states and price recovery | WATCH-07 | Needs a real server restart | Stop and restart the server with the tab open |
| Clean shutdown, health, no external requests | OPS-03, APP-02, UI-01 | Real process and network | Ctrl+C with the tab open; `curl /api/health`; check requests stay on localhost |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
