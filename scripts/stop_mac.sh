#!/usr/bin/env bash
# Stop and remove the FinAlly container. The finally-data volume is kept.
set -euo pipefail

CONTAINER=finally

docker info >/dev/null 2>&1 || { echo "Docker is not running." >&2; exit 1; }

if [[ -n "$(docker ps -aq --filter "name=^${CONTAINER}$")" ]]; then
  docker stop "$CONTAINER" >/dev/null
  docker rm "$CONTAINER" >/dev/null
  echo "FinAlly stopped. Data is kept in the finally-data volume."
else
  echo "FinAlly is not running."
fi
