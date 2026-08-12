# PySetu AI

**Enterprise AI Governance and Control Plane**

PySetu AI is a production-grade, multi-tenant SaaS platform that governs the full AI request lifecycle across agents, LLMs, MCP servers, and enterprise data sources.

## Capabilities

- OpenAI & Gemini Compatible Gateway
- Enterprise LLM Router
- MCP Governance Platform
- AI Security Gateway & Policy Engine
- AI Observability & Audit Platform
- Data Governance & DLP

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | Next.js, React, TypeScript, Tailwind CSS, shadcn/ui, Recharts, Zustand, TanStack Query |
| Backend | Python, FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery, OpenTelemetry |
| Security | JWT, RBAC, ABAC, OPA, Hashicorp Vault |
| Deployment | Docker, Docker Compose, Kubernetes-ready |

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.12+
- Docker & Docker Compose (optional)

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Backend

```bash
cd backend
pip install -r requirements.txt

# Start PostgreSQL (from repo root)
docker compose up postgres -d

# Migrate and seed
python -m alembic upgrade head
python -m app.db.seed

# Run API
uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

If port 8000 is in use, run `uvicorn app.main:app --reload --port 8001` and set `NEXT_PUBLIC_API_URL=http://localhost:8001/api/v1` in `frontend/.env.local`.

### Full Stack (Docker)

> **macOS external volume users:** If this repo lives on a volume under `/Volumes/`,
> always use `make` instead of raw `docker compose --build`. macOS creates hidden
> `._*` sidecar files with `xattr` metadata that Docker BuildKit cannot read, causing
> `operation not permitted` errors. The Makefile runs `dot_clean` automatically.
> See [`.agents/AGENTS.md`](.agents/AGENTS.md) for full details.

```bash
# From repo root — clean + build + start all services
make build

# Or with raw docker compose (only on Linux / non-external volumes)
docker compose --env-file .env.docker up --build -d
```

```bash
# Common make targets
make build          # dot_clean + rebuild all services
make build-backend  # dot_clean + rebuild backend only
make migrate        # run alembic upgrade head inside container
make ps             # show container status
make logs           # tail all logs
make restart        # full down + clean + rebuild
make down           # stop all containers
```

| Service  | URL |
|----------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8001 |
| API Docs | http://localhost:8001/docs |
| Mailhog (email) | http://localhost:8025 |

Sign in with `admin@acme.com` / `demo1234` (tenant: `acme`).

> Backend is mapped to host port **8001** by default to avoid conflicts with other services on 8000. Override via `.env.docker`.

### Kubernetes (Helm)

Chart path: `deploy/helm/pysetu`

```bash
# Build images (set NEXT_PUBLIC_API_URL to your ingress URL)
docker build -t pysetu/backend:latest ./backend
docker build -t pysetu/frontend:latest \
  --build-arg NEXT_PUBLIC_API_URL=http://pysetu.local/api/v1 ./frontend

# Local cluster profile (Minikube / kind)
helm upgrade --install pysetu ./deploy/helm/pysetu \
  -f ./deploy/helm/pysetu/values-minikube.yaml \
  --namespace pysetu --create-namespace

# Production overrides (example)
helm upgrade --install pysetu ./deploy/helm/pysetu \
  --set secrets.jwtSecretKey=<strong-secret> \
  --set postgresql.auth.password=<strong-password> \
  --set config.opaFailOpen=false \
  --set ingress.enabled=true \
  --set ingress.host=pysetu.example.com
```

The chart deploys backend, frontend, Celery worker/beat, PostgreSQL, Redis, OPA (with ABAC Rego policies), optional Ingress, and backend HPA.

### Production hardening

Before any non-dev deployment:

1. Copy [`.env.production.example`](.env.production.example) and fill secrets (never commit).
2. Generate or Vault-bootstrap JWT: [docs/security/jwt-secret-rotation.md](docs/security/jwt-secret-rotation.md)
3. Set `DEBUG=false`, enable Vault, and use strong database passwords.
4. Run `./scripts/generate-jwt-secret.sh` or `./scripts/vault-bootstrap-jwt-secret.sh`

### Air-gap (offline)

For isolated environments with no cloud LLM access:

```powershell
# Build transferable bundle (connected machine)
.\deploy\airgap\bundle.ps1 -Version 0.1.0

# On air-gapped host: extract archive and run .\install.ps1
```

See `deploy/airgap/README.md` for full instructions. Set `AIR_GAP_MODE=true` to disable cloud LLM upstreams.

### CI

GitHub Actions workflow (`.github/workflows/ci.yml`):

- Backend: Ruff + pytest
- Frontend: ESLint + production build
- Helm: `helm lint` + template render
- Docker: backend/frontend image build smoke test

## Project Structure

```
PySetu AI/
├── frontend/          # Next.js App Router UI
├── backend/           # FastAPI services
├── deploy/
│   ├── airgap/            # Offline bundle scripts (BL-032)
│   ├── helm/pysetu/   # Kubernetes Helm chart (BL-031)
│   └── opa/policies/      # OPA Rego policies (Docker Compose)
├── docs/              # Architecture, planning, progress, ADRs
├── .agents/AGENTS.md  # Agent rules — Docker, Alembic, macOS volume gotchas
├── Makefile           # Docker helpers (use instead of raw docker compose --build)
├── docker-compose.yml
└── README.md
```

## Documentation

See `/docs` for architecture, planning, progress tracking, ADRs, and agent handoffs.

## Development Phases

| Phase | Scope |
|-------|-------|
| Phase 1 | Foundation, Auth, Multi-Tenancy, Navigation, Dashboard |
| Phase 2 | Policy Studio, LLM Router, MCP Governance |
| Phase 3 | Audit Explorer, Compliance, Security Center |
| Phase 4 | Studio, Reporting, Analytics |
| Phase 5 | Air Gap, Kubernetes, Production Hardening |

## License

Proprietary — PySetu AI
