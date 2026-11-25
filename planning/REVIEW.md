# Change Review

Base: `ffbb3b4`  
Reviewed: all tracked and untracked working-tree changes on 2026-11-25.

## Findings

### P1 — The Stop hook bypasses the deduplicating wrapper

`.claude/settings.json:13` invokes `codex exec` directly instead of `scripts/run_review.sh`. Consequently every Claude Stop event launches a review even when the reviewable working tree has not changed, and `.claude/.last_review_hash` is never read or written. Point the hook at `./scripts/run_review.sh` so the fingerprint guard is actually used.

### P1 — Untracked filenames can execute shell code in the wrapper

`scripts/run_review.sh:17-18` substitutes each untracked filename directly into the source string passed to `sh -c`. A valid filename containing quotes or shell metacharacters is therefore parsed as shell syntax while the fingerprint is calculated; ordinary unusual filenames can also make fingerprinting fail. Pass filenames as positional arguments instead, for example with a loop whose body uses `cat -- "$path"`, and never interpolate a filename into shell source.

This path is currently dormant because the Stop hook bypasses the wrapper, but it becomes reachable when the preceding finding is fixed.

### P1 — Consolidation removes unresolved project review findings

The change deletes `planning/CDX_REVIEW.md` and `planning/CLDE_REVIEW.md`, which contain 239 lines of substantive findings about the stream contract, trade atomicity, API contracts, ticker lifecycle, and tests. Neither the new review automation nor `planning/old_REVIEW.md` preserves those findings; the latter only reviews this automation change. If one append-only review file is desired, migrate the still-open findings into it or archive the original documents before deleting them.

### P2 — The documented backend setup omits the test extra

`README.md:66-68` tells a fresh checkout to run `uv sync` followed by `uv run pytest`, but pytest and pytest-asyncio are declared only in the `dev` optional dependency group in `backend/pyproject.toml:15-20`. The documented sequence therefore does not install the test runner. Use `uv sync --extra dev` and/or `uv run --extra dev pytest`, consistent with the backend's dependency declaration.

### P2 — Configuration instructs users to copy a nonexistent file

`README.md:25` directs users to copy `.env.example`, but no such file exists in the working tree or in `HEAD`. Either add the example file with the three documented variables or describe creating `.env` directly. As written, the first configuration instruction fails.

## Verification

- `.claude/settings.json` parses successfully with `jq`.
- `scripts/run_review.sh` is executable and passes `bash -n`.
- `git diff --check HEAD` reports no whitespace errors.
- Compared every tracked modification/deletion and the complete contents of all untracked files against `HEAD` (`ffbb3b4`).

## Review checkpoint — 2026-11-25

No additional distinct findings were identified in a complete re-review of the current working tree. All five findings above remain applicable and unresolved.

Verification repeated against `HEAD` (`ffbb3b4`): reviewed every tracked change and deletion plus all four untracked files; confirmed `.claude/settings.json` is valid JSON, `scripts/run_review.sh` is executable and passes `bash -n`, and `git diff --check HEAD` reports no whitespace errors. Repository inspection also reconfirmed that `.env.example` is absent and that the backend test dependencies are declared only in the optional `dev` extra.

## Review checkpoint — 2026-11-25 (latest working tree)

No additional distinct findings were identified after reviewing every tracked modification/deletion and all untracked files against `HEAD` (`ffbb3b4`). The five findings above remain unresolved and applicable to the current tree.

Validation repeated: `.claude/settings.json` parses successfully; `scripts/run_review.sh` is executable and passes `bash -n`; `git diff --check HEAD` reports no whitespace errors; `.env.example` remains absent; and the backend test tools remain confined to the optional `dev` dependency group.
