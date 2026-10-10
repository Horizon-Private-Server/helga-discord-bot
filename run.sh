#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_PATH="$SCRIPT_DIR/config.json"

if command -v cygpath >/dev/null 2>&1; then
  CONFIG_PATH="$(cygpath -w "$CONFIG_PATH")"
fi

cd "$SCRIPT_DIR"
docker build . --network=host -t helga-discord-bot

echo "Starting ..."
docker rm -f helga-discord-bot >/dev/null 2>&1 || true
docker run -it --rm \
  --network=host \
  --env-file "$SCRIPT_DIR/src/.env" \
  -v "$CONFIG_PATH:/code/src/config/config.json:ro" \
  --name helga-discord-bot \
  helga-discord-bot