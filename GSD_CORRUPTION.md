# What the finally-gsd branch affected

Checked and fixed 2026-11-27. Times are local (+07). The "Problems found" section describes the state
**before** the fixes.

## Verdict

- Commit `55b5894` (`agent-teams`) was intact: no committed file was damaged and `git fsck` reported no errors.
- The problems were files and data **outside Git**, which switching branches does not remove or reset.
- All the GSD leftovers below have been fixed. App data was kept.

## Fixes applied

Backups are in `../finally-gsd-backup-2026-11-27/` (outside the repository).

| Problem | Fix |
|---|---|
| 1. Shared data volume | Backed up (`finally-data-volume.db`), then dropped `last_prices` and four GSD indexes. Row counts unchanged, integrity ok |
| 2. Local database | Backed up (`finally.db`) and removed. A new one is created on the next local run |
| 3. Stale frontend build | Removed, then rebuilt from this branch |
| 4. Wrong frontend packages | `npm ci` in `frontend/` and `test/`: Vitest 3.2.7, TypeScript 5.9.3, jsdom 26.1.0 |
| 5. Partial GSD install | 340 files archived (`claude-gsd-lib.tar`, compared file by file), then removed with the empty `.claude/.gsd-staging` |
| 6. Smaller leftovers | `uv sync --extra dev`; caches and old test output removed; `.planning/` archived (`planning-gsd.tar`) and removed |
| Page retried only once (not from GSD) | Fixed in `frontend/src/lib/useAccount.ts`, with a new test that fails without the fix |
| App image | Rebuilt with `scripts/start_mac.sh --build` |

## Verification after the fixes

| Check | Result |
|---|---|
| Backend tests and lint | 265 passed, lint clean |
| Frontend tests, type check and build | 26 passed, clean, succeeded |
| Browser tests against the rebuilt image (mock LLM) | 25 passed |
| Running app | Healthy; API requests return 200 |

Not tested: real LLM calls and real (Massive) market data.

## Branch history

`finally-gsd` did not start from `55b5894`. It split from `main`'s line at `4e051aa` (11:45), includes
`main`'s tip `1def24e`, and has none of the later `agent-teams` platform work. It has 66 commits of its own.

Its first commit, `7dc6485` ("Start of GSD process"), is where the old `frontend/src` design files were
removed. That commit is not on `agent-teams`.

## Problems found

### 1. Shared Docker data volume (affects the running app)

Until commit `bd50099` (17:45) gave it its own Docker names, `finally-gsd` used the volume `finally-data`.

- The volume now holds a GSD-only table, `last_prices` (12 rows, last saved 17:45:10), and GSD-named
  duplicate indexes such as `idx_chat_user_time`.
- One trade falls in the GSD session: **buy 1 JPM at $195.31 ($195.31), 17:37:48**. The records do not show
  whether you or an automated check made it.
- The other 6 trades (13:09 to 13:41) and the watchlist additions predate GSD's first commit.
- Integrity check: ok. Column definitions of the six app tables match the current code. The app's health,
  portfolio, watchlist and history requests all return 200.
- Effect: the extra table and indexes are unused by this branch. The data is mixed, not corrupted.

### 2. Local database `db/finally.db` written by GSD

- Last written 17:27. It has the GSD schema (`last_prices`, GSD index names) and no trades.
- Used only when the backend runs outside Docker. Chat records saved by one branch may not suit the other
  (GSD commit `6cceda7` had to ignore actions saved by an earlier version).

### 3. Stale frontend build: `frontend/out` and `frontend/.next`

- Dated 16:40, during the GSD session.
- Running the backend outside Docker serves `frontend/out`, so you would likely see the **GSD page on the
  `agent-teams` backend**.
- Docker is not affected: both folders are excluded from the image.

### 4. Wrong frontend packages in `frontend/node_modules`

- Installed: Vitest 5.1.2, TypeScript 6.0.3, jsdom 31. These match `finally-gsd`'s `package.json`.
- `agent-teams` asks for Vitest 3.2.7, TypeScript 5.9.3, jsdom 26. Local tests therefore ran on the wrong
  versions. Docker is not affected.

### 5. Partial GSD install left in `.claude/`

- 340 files remain in `lib/` folders under `.claude/gsd-core`, `.claude/hooks` and `.claude/scripts`
  (dated 14:00 to 15:00). The rest of GSD disappears when you leave `finally-gsd`.
- Cause: they are not tracked on either branch, so Git leaves them in place. `agent-teams` also hides them
  from `git status` with its `lib/` ignore rule.
- **These files are not in `finally-gsd`'s commits.** A fresh clone of that branch would lack them, and GSD
  would likely fail there. Do not delete them without a copy.

### 6. Smaller leftovers

| Item | Note |
|---|---|
| `__pycache__` files for GSD modules (`server.py`, `identity.py` and others) | Python ignores them without their source; safe to delete |
| `backend/.venv` | Package versions had drifted; `uv run` during these checks replaced 6 packages. Run `uv sync --extra dev` to match exactly |
| `.planning/state.json`, `.planning/research/` | GSD state; `state.json` shows as untracked on this branch |
| `test/test-results` | Dated 17:45, from GSD |
| `finally-gsd` image and `finally-gsd-data` volume | Separate; no effect. Its start script also defaults to port 8000, so run one app at a time |

## Still open

- **The JPM trade was kept.** To start again with $10,000 (loses all trades and chat):
  `scripts/stop_mac.sh && docker volume rm finally-data && scripts/start_mac.sh`
- **`.claude/settings.local.json` and `.env` were not read.** The settings file is not in Git, so it carries
  across branches. Check `/hooks` for leftover GSD entries.
- **`finally-gsd` image and `finally-gsd-data` volume** were left. They are separate. That app also defaults
  to port 8000, so run one at a time.
- **Frontend test tools** (Vitest, tinypool) have known vulnerabilities. Development only; the fix is a major
  upgrade.
- **Node 20** in the `Dockerfile` has reached end of life.

## Using GSD again

Give `finally-gsd` its own folder, so its untracked files and packages stay apart. From the project folder:

```bash
git worktree add ../finally-gsd finally-gsd
tar -xf ../finally-gsd-backup-2026-11-27/claude-gsd-lib.tar -C ../finally-gsd
tar -xf ../finally-gsd-backup-2026-11-27/planning-gsd.tar -C ../finally-gsd
```

The first `tar` restores files that are **not in `finally-gsd`'s commits**. Consider committing them there.
`.env` and local settings are not copied to the new folder. Docker volumes are shared by name, so keep the
separate `finally-gsd` names.
