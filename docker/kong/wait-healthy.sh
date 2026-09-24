#!/bin/sh
set -e

for i in $(seq 1 30); do
  STATUS=$(docker compose ps kong --format json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['Health'])" 2>/dev/null || echo "unknown")
  if [ "$STATUS" = "healthy" ]; then
    echo "Kong is healthy"
    exit 0
  fi
  echo "Waiting for Kong... ($i/30)"
  sleep 3
done

echo "Kong did not become healthy in time"
docker compose logs kong
exit 1
