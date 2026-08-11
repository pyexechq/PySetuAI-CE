#!/usr/bin/env bash
# Export Ollama model blobs for offline air-gap bundles (run on internet-connected host).
set -euo pipefail

MODELS="${OLLAMA_MODELS:-llama3.2}"
OUTPUT_PATH="${1:-models/ollama-models.tar.gz}"
OLLAMA_IMAGE="${OLLAMA_IMAGE:-ollama/ollama:0.5.4}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

IFS=',' read -ra MODEL_LIST <<< "${MODELS}"

output_dir="$(dirname "${OUTPUT_PATH}")"
mkdir -p "${output_dir}"
output_abs="$(cd "${output_dir}" && pwd)/$(basename "${OUTPUT_PATH}")"

vol="pysetu-ollama-export-$$"
container="pysetu-ollama-export-$$"

cleanup() {
  docker rm -f "${container}" >/dev/null 2>&1 || true
  docker volume rm "${vol}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> Exporting Ollama models: ${MODEL_LIST[*]}"
docker volume create "${vol}" >/dev/null
docker run -d --name "${container}" -v "${vol}:/root/.ollama" "${OLLAMA_IMAGE}" >/dev/null
sleep 5

for model in "${MODEL_LIST[@]}"; do
  model="$(echo "${model}" | xargs)"
  [[ -z "${model}" ]] && continue
  echo "    pulling ${model}..."
  docker exec "${container}" ollama pull "${model}"
done

docker exec "${container}" sh -c "tar czf /tmp/ollama-models.tar.gz -C /root/.ollama ."
docker cp "${container}:/tmp/ollama-models.tar.gz" "${output_abs}"

python3 - <<PY
import hashlib, json, pathlib
archive = pathlib.Path("${output_abs}")
manifest = {
    "models": [m.strip() for m in "${MODELS}".split(",") if m.strip()],
    "archive": archive.name,
    "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
    "ollama_image": "${OLLAMA_IMAGE}",
}
path = pathlib.Path("${output_dir}") / "ollama-models.manifest.json"
path.write_text(json.dumps(manifest, indent=2))
print("Models archive:", archive)
print("SHA256:", manifest["sha256"])
print("Manifest:", path)
PY

echo "==> Export complete: ${output_abs}"
