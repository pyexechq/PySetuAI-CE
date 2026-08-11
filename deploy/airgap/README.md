# Air-Gap Offline Bundle (BL-032)

Deploy PySetu AI in environments with **no outbound internet** access.

## What's included

| Artifact | Purpose |
|----------|---------|
| `docker-compose.airgap.yml` | Dev/build profile (builds from source, bundled Ollama) |
| `deploy/airgap/docker-compose.offline.yml` | Offline profile (pre-built images only) |
| `deploy/airgap/bundle.sh` / `bundle.ps1` | Create transferable offline bundle |
| `deploy/airgap/export-ollama-models.*` | Pull + tarball Ollama models on connected host |
| `deploy/airgap/import-ollama-models.*` | Import model tarball into running Ollama (install) |
| `deploy/airgap/install.sh` / `install.ps1` | Install from bundle on isolated host |
| `deploy/helm/pysetu/values-airgap.yaml` | Kubernetes air-gap values |

## Quick start (connected machine)

Build the offline bundle:

```powershell
# Windows — images only
.\deploy\airgap\bundle.ps1 -Version 0.1.0

# Windows — include llama3.2 in the bundle (~ adds several GB)
.\deploy\airgap\bundle.ps1 -Version 0.1.0 -OllamaModels llama3.2
```

```bash
# Linux / macOS
chmod +x deploy/airgap/bundle.sh
./deploy/airgap/bundle.sh 0.1.0

# With bundled Ollama models
OLLAMA_MODELS=llama3.2 ./deploy/airgap/bundle.sh 0.1.0
```

Output: `dist/pysetu-airgap-0.1.0.zip` (or `.tar.gz` on Linux)

## Install on air-gapped host

1. Transfer and extract the archive
2. Verify `manifest.json` SHA256 matches `images/pysetu-images.tar`
3. Run install:

```powershell
.\install.ps1
```

```bash
chmod +x install.sh
./install.sh
```

4. **Install auto-imports** `models/ollama-models.tar.gz` when present; otherwise load manually:

```bash
docker compose --env-file .env.airgap -f docker-compose.airgap.yml exec ollama ollama pull llama3.2
```

### Export models separately (connected host)

```powershell
.\deploy\airgap\export-ollama-models.ps1 -Models llama3.2 -OutputPath .\models\ollama-models.tar.gz
```

Copy the `models/` folder into the bundle before transfer, then re-run `import-ollama-models.ps1` on the air-gapped host.

5. Open http://localhost:3000 — login `admin@acme.com` / `demo1234`

## Air-gap behavior

When `AIR_GAP_MODE=true`:

- Cloud LLM keys (OpenAI/Gemini) are **ignored** — gateway uses Ollama only
- OTLP telemetry export disabled (console only)
- SMTP disabled by default
- OPA fail-closed (`OPA_FAIL_OPEN=false`)

Health check reports air-gap status: `GET /health` → `"air_gap_mode": "true"`

## Production checklist

- [ ] Change `JWT_SECRET_KEY` and `POSTGRES_PASSWORD` in `.env.airgap`
- [ ] Bundle Ollama models with `-OllamaModels` or `export-ollama-models.*` (recommended for fully offline inference)
- [ ] Use Helm + `values-airgap.yaml` for Kubernetes deployments
- [ ] Replace Vault dev mode with production Vault (optional)

## Kubernetes

```bash
helm upgrade --install pysetu ./helm/pysetu \
  -f ./helm/pysetu/values-airgap.yaml \
  --namespace pysetu --create-namespace
```

Bundle Ollama models separately for fully offline K8s inference.
