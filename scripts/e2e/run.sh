#!/usr/bin/env bash
# End-to-end smoke test: starts a fresh Home Assistant in Docker with this
# integration, onboards it, and drives the panel with a headless browser.
# Screenshots end up in scripts/e2e/out/.
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/../.."
ROOT="$(pwd -W 2>/dev/null || pwd)"
HA_IMAGE="${HA_IMAGE:-ghcr.io/home-assistant/home-assistant:2026.10}"
PYTHON="${PYTHON:-python3}"
$PYTHON --version >/dev/null 2>&1 || PYTHON="py -3"

docker rm -f pm-ha-e2e >/dev/null 2>&1 || true
rm -rf scripts/e2e/out && mkdir -p scripts/e2e/out/config
cp scripts/e2e/configuration.yaml scripts/e2e/out/config/configuration.yaml
docker run -d --name pm-ha-e2e -p 8124:8123 -e TZ=Europe/Berlin \
  -v "$ROOT/scripts/e2e/out/config:/config" \
  -v "$ROOT/custom_components:/config/custom_components" \
  "$HA_IMAGE" >/dev/null
trap 'docker logs pm-ha-e2e > scripts/e2e/out/ha.log 2>&1; docker rm -f pm-ha-e2e >/dev/null' EXIT

$PYTHON scripts/e2e/onboard.py >/dev/null
docker run --rm --add-host=host.docker.internal:host-gateway \
  -v "$ROOT/scripts/e2e:/e2e" -v "$ROOT/scripts/e2e/out:/out" \
  mcr.microsoft.com/playwright/python:v1.49.0-noble \
  sh -c "pip install -q playwright==1.49.0 2>/dev/null; python /e2e/ui_test.py"
