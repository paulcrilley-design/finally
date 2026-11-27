#!/usr/bin/env bash
# Build (if needed) and run FinAlly in Docker. Safe to run repeatedly.
# Usage: scripts/start_mac.sh [--build] [--open]
# Variables set in the calling shell override .env, e.g. LLM_MOCK=true scripts/start_mac.sh
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE=finally
CONTAINER=finally
VOLUME=finally-data
URL=http://localhost:8000

build=false
open_browser=false
for arg in "$@"; do
  case "$arg" in
    --build) build=true ;;
    --open) open_browser=true ;;
    *) echo "Usage: $0 [--build] [--open]" >&2; exit 2 ;;
  esac
done

docker info >/dev/null 2>&1 || { echo "Docker is not running." >&2; exit 1; }

if $build || [[ -z "$(docker images -q "$IMAGE")" ]]; then
  docker build -t "$IMAGE" .
fi

# Always recreate the container so a new image or changed settings take effect.
if [[ -n "$(docker ps -aq --filter "name=^${CONTAINER}$")" ]]; then
  docker stop "$CONTAINER" >/dev/null
  docker rm "$CONTAINER" >/dev/null
fi

args=(-d --name "$CONTAINER" -p 127.0.0.1:8000:8000 -v "$VOLUME:/app/db")
if [[ -f .env ]]; then
  args+=(--env-file .env)
else
  echo "No .env file found: chat needs OPENROUTER_API_KEY unless LLM_MOCK=true." >&2
fi
# -e wins over --env-file. "-e NAME" passes the caller's value without putting it on the command line.
for name in LLM_MOCK OPENROUTER_API_KEY MASSIVE_API_KEY MASSIVE_MODE MASSIVE_POLL_INTERVAL \
  MARKET_FORCE_SIMULATOR SIM_SEED; do
  if [[ -n "${!name+set}" ]]; then
    export "${name?}"
    args+=(-e "$name")
  fi
done
# Container paths are fixed, whatever .env says.
args+=(-e DB_PATH=/app/db/finally.db -e STATIC_DIR=/app/static)

docker run "${args[@]}" "$IMAGE" >/dev/null

for _ in $(seq 60); do
  if curl -fsS --max-time 2 "$URL/api/health" >/dev/null 2>&1; then
    echo "FinAlly is running at $URL"
    if $open_browser; then open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null || true; fi
    exit 0
  fi
  sleep 1
done

echo "FinAlly did not become healthy. See: docker logs $CONTAINER" >&2
exit 1
