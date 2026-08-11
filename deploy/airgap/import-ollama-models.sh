#!/usr/bin/env bash
# Import bundled Ollama models into a running air-gap compose stack.
set -euo pipefail

BUNDLE_DIR="${1:-.}"
COMPOSE_FILE="${2:-docker-compose.airgap.yml}"
ARCHIVE="${3:-models/ollama-models.tar.gz}"
ENV_FILE="${4:-.env.airgap}"

archive_path="${BUNDLE_DIR}/${ARCHIVE}"
manifest_path="${BUNDLE_DIR}/models/ollama-models.manifest.json"

if [[ ! -f "${archive_path}" ]]; then
  echo "No bundled Ollama models at ${archive_path} — skip import."
  exit 0
fi

if [[ -f "${manifest_path}" ]]; then
  expected="$(python3 -c "import json; print(json.load(open('${manifest_path}'))['sha256'])")"
  actual="$(sha256sum "${archive_path}" | awk '{print $1}')"
  if [[ "${expected}" != "${actual}" ]]; then
    echo "Ollama models SHA256 mismatch!" >&2
    exit 1
  fi
  echo "Ollama models checksum verified."
fi

cd "${BUNDLE_DIR}"
compose_args=(-f "${COMPOSE_FILE}")
[[ -f "${ENV_FILE}" ]] && compose_args=(--env-file "${ENV_FILE}" "${compose_args[@]}")

echo "==> Waiting for Ollama container..."
for _ in $(seq 1 30); do
  cid="$(docker compose "${compose_args[@]}" ps -q ollama 2>/dev/null || true)"
  [[ -n "${cid}" ]] && break
  sleep 2
done

if [[ -z "${cid:-}" ]]; then
  echo "Ollama container not found. Start the stack first." >&2
  exit 1
fi

echo "==> Importing models into Ollama volume..."
docker cp "${archive_path}" "${cid}:/tmp/ollama-models.tar.gz"
docker exec "${cid}" sh -c "tar xzf /tmp/ollama-models.tar.gz -C /root/.ollama && rm -f /tmp/ollama-models.tar.gz"

echo "==> Installed models:"
docker exec "${cid}" ollama list
echo "Ollama model import complete."
