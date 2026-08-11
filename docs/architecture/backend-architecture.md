# Backend Architecture

## Stack

- **Framework:** FastAPI
- **ORM:** SQLAlchemy 2.0 (async)
- **Database:** PostgreSQL 16
- **Cache/Queue:** Redis 7 + Celery
- **Auth:** JWT (python-jose) + bcrypt (passlib)
- **Observability:** OpenTelemetry (planned)

## Directory Structure

```
backend/app/
├── main.py              # FastAPI app, CORS, routers
├── config.py            # Pydantic Settings
├── core/
│   └── security.py      # JWT, password hashing
├── models/
│   └── tenant.py        # Tenant, User SQLAlchemy models
├── schemas/
│   └── auth.py          # Pydantic request/response models
└── api/v1/
    └── router.py        # Versioned API routes
```

## API Endpoints (v1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/auth/login` | JWT login |
| GET | `/api/v1/auth/me` | Current user |
| GET | `/api/v1/tenants/current` | Current tenant |
| GET | `/api/v1/dashboard/metrics` | Dashboard KPIs |

## Multi-Tenant Isolation

1. JWT payload includes `tenant_id` and `role`
2. Dependency injection extracts tenant from token
3. All database queries filter by `tenant_id`
4. Row-level security planned for PostgreSQL

## Roles (RBAC)

| Role | Permissions |
|------|------------|
| platform_admin | Cross-tenant management |
| tenant_admin | Full tenant configuration |
| security_admin | Policies, MCP governance |
| compliance_officer | Compliance, audit read |
| auditor | Read-only audit access |
| developer | Studio, gateway usage |

## Planned Services (Phase 2+)

- `gateway/` — OpenAI/Gemini proxy with inspection
- `router/` — LLM routing engine
- `policy/` — OPA integration
- `mcp/` — MCP registry and governance
- `audit/` — Request/response trace ingestion
- `dlp/` — PII/secret detection pipeline
