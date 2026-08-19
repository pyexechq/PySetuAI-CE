#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Clear macOS resource-fork files (AppleDouble) that can corrupt the build
dot_clean .

# Rebuild and restart the frontend container
docker compose up -d --build frontend

echo "Frontend rebuild complete. Checking status..."
docker ps --filter "name=frontend" --format '{{.Names}}\t{{.Status}}'
