#!/bin/sh
set -e

for i in $(seq 1 30); do
  STATUS=$(docker inspect --format='{{.State.Health.Status}}' ai-commerce-platform-kong-1 2>/dev/null || echo "unknown")
  if [ "$STATUS" = "healthy" ]; then
    echo "Kong is healthy"
    exit 0
  fi
  echo "Waiting for Kong... ($i/30) status=$STATUS"
  sleep 3
done

echo "Kong did not become healthy in time"
docker compose logs kong
exit 1
