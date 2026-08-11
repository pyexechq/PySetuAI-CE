#!/usr/bin/env bash
# Install HelixGuard AI from an offline bundle (run inside extracted bundle directory).
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_ARCHIVE="${BUNDLE_DIR}/images/helixguard-images.tar"
COMPOSE_FILE="${BUNDLE_DIR}/docker-compose.airgap.yml"
MANIFEST="${BUNDLE_DIR}/manifest.json"

if [[ ! -f "${IMAGE_ARCHIVE}" ]]; then
  echo "Missing ${IMAGE_ARCHIVE}. Run bundle.sh on a connected machine first." >&2
  exit 1
fi

if [[ -f "${MANIFEST}" ]] && command -v sha256sum >/dev/null 2>&1; then
  expected="$(python3 -c "import json; print(json.load(open('${MANIFEST}'))['sha256'])")"
  actual="$(sha256sum "${IMAGE_ARCHIVE}" | awk '{print $1}')"
  if [[ "${expected}" != "${actual}" ]]; then
    echo "SHA256 mismatch! Expected ${expected}, got ${actual}" >&2
    exit 1
  fi
  echo "Checksum verified."
fi

echo "==> Loading container images (offline)..."
docker load -i "${IMAGE_ARCHIVE}"

echo "==> Starting air-gapped stack..."
docker compose --env-file "${BUNDLE_DIR}/.env.airgap" -f "${COMPOSE_FILE}" up -d

if [[ -x "${BUNDLE_DIR}/import-ollama-models.sh" ]]; then
  echo "==> Importing bundled Ollama models (if present)..."
  bash "${BUNDLE_DIR}/import-ollama-models.sh" "${BUNDLE_DIR}" "${COMPOSE_FILE}"
fi

echo ""
echo "HelixGuard air-gap stack is starting."
echo "  UI:      http://localhost:3000"
echo "  API:     http://localhost:8001"
echo "  Health:  http://localhost:8001/health"
echo ""
if [[ ! -f "${BUNDLE_DIR}/models/ollama-models.tar.gz" ]]; then
  echo "Load a local LLM model manually:"
  echo "  docker compose -f ${COMPOSE_FILE} exec ollama ollama pull llama3.2"
fi
echo ""
echo "Demo login: admin@acme.com / demo1234 (tenant: acme)"
