---
phase: 05-one-command-run-and-release
status: complete
requirements-completed: [APP-04, UI-02, OPS-01, OPS-02, TEST-01, TEST-02, TEST-03]
---

# Phase 5 Summary: One-command run and release

## Built

- `Dockerfile` (Node 24 build, Python 3.12 run, non-root user) and `.dockerignore`.
- `scripts/start_mac.sh` and `scripts/stop_mac.sh`.
- `test/`: Playwright 1.65.1 with the seven section 12 scenarios, saved data after stop and
  start, and phone and tablet width checks.
- Unit tests added: refused watchlist actions, a failed chat action, stream-driven price flash,
  watchlist add and remove errors.

## Found while building

- A `finally-data` volume already existed with a root-owned database, which the non-root app
  could not write. The start script now gives the app user ownership before starting. Checked on
  a copy; the original volume was not changed. Its data is reused on the first start, so the app
  does not necessarily open at $10,000 as the plan said.
- No layout changes were needed for narrow screens. On a phone the positions table scrolls
  sideways inside its panel, as the plan allows.

## Verification

- Backend 263 passed, ruff clean; frontend 86 passed, lint and typecheck passed; production
  build passed inside Docker.
- Playwright: 10 passed against the container in mock mode.
- Scripts: repeat start and stop, rebuild while running, busy port, clean stop with a price
  stream open, saved data, and a mounted `.env` (dummy file).
- Phone (390 px) and tablet (768 px) screenshots checked.
- Not checked: Linux, `--open`, and live AI chat inside the container with a real key.
