#!/usr/bin/env bash
# Package HelixGuard AI for offline / air-gapped installation.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:-0.1.0}"
OLLAMA_MODELS="${OLLAMA_MODELS:-}"
OUTPUT_DIR="${ROOT}/dist/helixguard-airgap-${VERSION}"
IMAGE_ARCHIVE="${OUTPUT_DIR}/images/helixguard-images.tar"
COMPOSE_BUILD="docker-compose.airgap.yml"
BACKEND_TAG="helixguard/backend:${VERSION}"
FRONTEND_TAG="helixguard/frontend:${VERSION}"

echo "==> HelixGuard air-gap bundle v${VERSION}"
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}/images"

cd "${ROOT}"

echo "==> Building and tagging application images..."
docker compose -f "${COMPOSE_BUILD}" build
project_name="$(basename "${ROOT}" | tr '[:upper:]' '[:lower:]' | tr -d ' ')"
built_backend="${project_name}-backend:latest"
built_frontend="${project_name}-frontend:latest"
docker tag "${built_backend}" "${BACKEND_TAG}"
docker tag "${built_frontend}" "${FRONTEND_TAG}"

THIRD_PARTY_IMAGES=(
  "postgres:16-alpine"
  "redis:7-alpine"
  "hashicorp/vault:1.17"
  "openpolicyagent/opa:0.68.0"
  "ollama/ollama:0.5.4"
)

echo "==> Pulling third-party images..."
for image in "${THIRD_PARTY_IMAGES[@]}"; do
  docker pull "${image}"
done

SAVE_IMAGES=("${THIRD_PARTY_IMAGES[@]}" "${BACKEND_TAG}" "${FRONTEND_TAG}")

echo "==> Saving images to ${IMAGE_ARCHIVE}..."
docker save -o "${IMAGE_ARCHIVE}" "${SAVE_IMAGES[@]}"

echo "==> Copying deployment artifacts..."
cp "${ROOT}/deploy/airgap/docker-compose.offline.yml" "${OUTPUT_DIR}/docker-compose.airgap.yml"
cp -r "${ROOT}/deploy/helm" "${OUTPUT_DIR}/"
cp -r "${ROOT}/deploy/opa" "${OUTPUT_DIR}/"
cp "${ROOT}/deploy/airgap/install.sh" "${OUTPUT_DIR}/"
cp "${ROOT}/deploy/airgap/install.ps1" "${OUTPUT_DIR}/"
cp "${ROOT}/deploy/airgap/import-ollama-models.sh" "${OUTPUT_DIR}/"
cp "${ROOT}/deploy/airgap/import-ollama-models.ps1" "${OUTPUT_DIR}/"
cp "${ROOT}/deploy/airgap/manifest.template.json" "${OUTPUT_DIR}/manifest.json"

if [[ -n "${OLLAMA_MODELS}" ]]; then
  echo "==> Bundling Ollama models: ${OLLAMA_MODELS}"
  mkdir -p "${OUTPUT_DIR}/models"
  OLLAMA_MODELS="${OLLAMA_MODELS}" bash "${ROOT}/deploy/airgap/export-ollama-models.sh" "${OUTPUT_DIR}/models/ollama-models.tar.gz"
fi

cat > "${OUTPUT_DIR}/.env.airgap" <<EOF
HELIXGUARD_BACKEND_IMAGE=${BACKEND_TAG}
HELIXGUARD_FRONTEND_IMAGE=${FRONTEND_TAG}
JWT_SECRET_KEY=airgap-change-me-before-production
POSTGRES_PASSWORD=helixguard-airgap
NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1
EOF

python3 - <<PY
import hashlib, json, pathlib
root = pathlib.Path("${OUTPUT_DIR}")
archive = root / "images/helixguard-images.tar"
sha = hashlib.sha256(archive.read_bytes()).hexdigest()
manifest = json.loads((root / "manifest.json").read_text())
manifest["version"] = "${VERSION}"
manifest["created_at"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
manifest["images_archive"] = archive.name
manifest["sha256"] = sha
manifest["images"] = {"backend": "${BACKEND_TAG}", "frontend": "${FRONTEND_TAG}"}
model_manifest = root / "models" / "ollama-models.manifest.json"
if model_manifest.exists():
    manifest["ollama_models"] = json.loads(model_manifest.read_text())
(root / "manifest.json").write_text(json.dumps(manifest, indent=2))
print("SHA256:", sha)
PY

ARCHIVE="${ROOT}/dist/helixguard-airgap-${VERSION}.tar.gz"
tar -czf "${ARCHIVE}" -C "${ROOT}/dist" "helixguard-airgap-${VERSION}"

echo ""
echo "Bundle ready:"
echo "  Directory: ${OUTPUT_DIR}"
echo "  Archive:   ${ARCHIVE}"
