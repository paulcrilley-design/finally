# FinAlly: GSD guide

AI trading workstation: live prices, simulated portfolio, LLM chat that trades. One Docker container, port 8000.
Core value: prices stream, trades fill correctly, and portfolio, cash and P&L numbers are right.

## Where the detail is (read on demand)

- Project, constraints, decisions: `.planning/PROJECT.md`
- Status: `.planning/STATE.md`, `ROADMAP.md`; v1.0 requirements and phases: `.planning/milestones/`
- Stack, conventions, architecture, testing, concerns: `.planning/codebase/*.md`
- LLM calls: `.claude/skills/cerebras/SKILL.md`

## Commands (from `backend/`)

```bash
uv sync --extra dev
uv run --extra dev pytest
uv run --extra dev ruff check .
```

## Gotchas

- Call `normalize_ticker()` before any price cache lookup; a missing price means reject the trade, never substitute one.
- Leave `MASSIVE_API_KEY` empty: the real data path is deferred.
- Run uvicorn with `--timeout-graceful-shutdown 3`.
- The frontend is written fresh to `planning/OUI_FORMAT.md`; the old design files stay deleted.

## GSD workflow

Before changing files, start through a GSD command: `/gsd-fast` (trivial), `/gsd-quick` (small fixes, docs),
`/gsd-debug` (bugs), `/gsd-execute-phase` (planned work). Edit directly only if the user asks to bypass GSD.
