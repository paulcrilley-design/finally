# Phase 5: One-Command Run and Release (short plan, built without GSD)

Status: approved and built (see 05-SUMMARY.md). Requirements: OPS-01, OPS-02, APP-04, UI-02, TEST-01 to 03.

## New packages and images

- `@playwright/test==1.65.1` (13 Nov 2026), pinned, in a new `test/package.json`, plus its
  Chromium browser download.
- Docker images: `node:24-slim` (build) and `python:3.12-slim` (run), with `uv` copied from its
  official image at a pinned version. `planning/PLAN.md` says Node 20, which is out of support.
- No new app dependencies.

## Docker

- `Dockerfile`: build the static frontend, then install the backend from `uv.lock` without dev
  tools, serve both on port 8000 as a non-root user, with `--timeout-graceful-shutdown 3`.
- `.dockerignore` keeps `.env`, `db/`, installs and build output out of the image.
- **`.env`:** mounted read-only when the container starts, never built in. This departs from
  `--env-file` in the plan, which would pass quoted values through with the quotes. Without a
  `.env` the app still runs; only live chat is unavailable.
- **Data:** named volume `finally-data` at `/app/db`. The current local `db/finally.db` is not
  copied in, so the container starts fresh with $10,000.

## Scripts (macOS/Linux)

- `scripts/start_mac.sh`: builds if there is no image or with `--build`, starts the container,
  waits for `/api/health`, prints the URL. `--open` also opens the browser (off by default).
- The port is published to this machine only (`127.0.0.1:8000`).
- Already running: print the URL and succeed. Port 8000 used by something else: stop with a
  clear message, never kill it.
- `scripts/stop_mac.sh`: stops and removes the container, keeps the volume.
- Container name, volume and port can be overridden, so tests never touch your data.

## Layout (UI-02)

Check every panel at 390 px and 768 px wide and fix any horizontal page scroll or unusable
control. The wide desktop layout stays as it is. Wide tables may scroll inside their panel.

## Tests

- **Unit (TEST-01, 02):** compare existing tests with the requirement lists and add only what is
  missing.
- **End to end (TEST-03):** Playwright from the host against the container, started by the start
  script with `LLM_MOCK=true` and a throwaway test volume. All seven section 12 scenarios; stream
  reconnection is tested by restarting the test container. Also checks data survives a restart.

## Build order (one run, no stops)

1. Dockerfile, ignore file and scripts; check start, stop, repeat runs and persistence.
2. Responsive fixes.
3. Unit test gaps, then Playwright.
4. Backend and frontend tests, lint, typecheck, Playwright run, browser check.
5. README, GSD records, `05-SUMMARY.md`, commit and push.

Not included: cloud deployment, Windows scripts, the Massive data source.
