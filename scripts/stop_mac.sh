#!/usr/bin/env bash
# Stop FinAlly (macOS/Linux). Safe to run more than once. Your data volume is kept.
set -euo pipefail

CONTAINER="${FINALLY_CONTAINER:-finally}"

fail() {
  echo "Error: $*" >&2
  exit 1
}

command -v docker >/dev/null || fail "Docker is not installed."
docker info >/dev/null 2>&1 || fail "Docker is not running."

if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
  docker stop "$CONTAINER" >/dev/null
  docker rm "$CONTAINER" >/dev/null
  echo "FinAlly stopped. Your data is kept."
else
  echo "FinAlly is not running."
fi
