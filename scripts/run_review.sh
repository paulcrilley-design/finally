#!/usr/bin/env bash
# Runs the fixed Codex review of all changes since the last commit.
# Takes no arguments, so it cannot be used to pass other options to codex.
#
# Skips the review when the reviewable changes are identical to the last
# successfully reviewed set. planning/REVIEW.md (the review's own output) and
# the fingerprint file are excluded so the review never triggers itself.
set -euo pipefail
cd "$(dirname "$0")/.."

STATE_FILE=".claude/.last_review_hash"
EXCLUDES=(':(exclude)planning/REVIEW.md' ':(exclude).claude/.last_review_hash')

fingerprint() {
  {
    git diff HEAD -- . "${EXCLUDES[@]}"
    git ls-files --others --exclude-standard -z -- . "${EXCLUDES[@]}" |
      xargs -0 -I{} sh -c 'echo "== {}"; cat "{}"' 2>/dev/null
  } | shasum -a 256 | cut -d' ' -f1
}

current="$(fingerprint)"
if [[ -f "$STATE_FILE" && "$(cat "$STATE_FILE")" == "$current" ]]; then
  echo "run_review: no changes since last review, skipping."
  exit 0
fi

codex exec 'please review all changes since the last commit and write your feedback to planning/REVIEW.md'
echo "$current" > "$STATE_FILE"
