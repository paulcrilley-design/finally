#!/usr/bin/env bash
# Start FinAlly in Docker (macOS/Linux). Safe to run more than once.
#   --build  rebuild the image and replace the running container
#   --open   open the app in the browser
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${FINALLY_IMAGE:-finally}"
CONTAINER="${FINALLY_CONTAINER:-finally}"
VOLUME="${FINALLY_VOLUME:-finally-data}"
PORT="${FINALLY_PORT:-8000}"
ENV_FILE="${FINALLY_ENV_FILE-$ROOT/.env}" # set to empty to run without one

fail() {
  echo "Error: $*" >&2
  exit 1
}

build=false
open_browser=false
for arg in "$@"; do
  case "$arg" in
    --build) build=true ;;
    --open) open_browser=true ;;
    *) fail "unknown option '$arg' (use --build or --open)" ;;
  esac
done

command -v docker >/dev/null || fail "Docker is not installed."
docker info >/dev/null 2>&1 || fail "Docker is not running. Start Docker Desktop and try again."

finish() {
  echo "FinAlly is running at http://localhost:$1"
  if $open_browser; then
    if command -v open >/dev/null; then
      open "http://localhost:$1"
    elif command -v xdg-open >/dev/null; then
      xdg-open "http://localhost:$1"
    fi
  fi
  exit 0
}

if $build || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Building the Docker image..."
  docker build -t "$IMAGE" "$ROOT"
fi

state="$(docker container inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || true)"
if [ "$state" = true ] && ! $build; then
  mapping="$(docker port "$CONTAINER" 8000/tcp | head -n 1)"
  finish "${mapping##*:}"
fi
if [ -n "$state" ]; then
  docker rm -f "$CONTAINER" >/dev/null
fi

if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
  fail "port $PORT is already in use by another program. Stop it, or set FINALLY_PORT."
fi

# The app does not run as root, so it must own the data, including any saved by an
# image that did run as root.
docker run --rm --user 0 -v "$VOLUME:/app/db" "$IMAGE" chown -R finally /app/db ||
  fail "the data volume '$VOLUME' could not be prepared."

args=(-d --name "$CONTAINER" -p "127.0.0.1:$PORT:8000" -v "$VOLUME:/app/db")
if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
  args+=(-v "$ENV_FILE:/app/.env:ro")
else
  echo "No .env file: live AI chat will be unavailable."
fi
# A value set in your shell wins over the one in .env.
if [ -n "${LLM_MOCK+set}" ]; then
  args+=(-e "LLM_MOCK=$LLM_MOCK")
fi

if ! docker run "${args[@]}" "$IMAGE" >/dev/null; then
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  fail "the container could not be started."
fi

for _ in $(seq 60); do
  if curl -fs -m 2 "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then
    finish "$PORT"
  fi
  [ "$(docker container inspect -f '{{.State.Running}}' "$CONTAINER")" = true ] || break
  sleep 1
done
docker logs --tail 40 "$CONTAINER" >&2
fail "the app did not become healthy. The log is above."
