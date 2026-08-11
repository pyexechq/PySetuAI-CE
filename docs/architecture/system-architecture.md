# System Architecture

## Overview

HelixGuard AI is a multi-tenant Enterprise AI Control Plane that sits between AI agents, MCP servers, enterprise data sources, and LLMs.

```
┌─────────────┐     ┌──────────────────────────────────┐     ┌─────────────┐
│  AI Agents  │────▶│         HelixGuard AI            │────▶│    LLMs     │
│  & Users    │     │  Gateway │ Router │ Policy │ DLP  │     │ OpenAI/Gemini│
└─────────────┘     │  MCP Gov │ Audit  │ Compliance     │     └─────────────┘
       │            └──────────────────────────────────┘            │
       │                          │                                  │
       ▼                          ▼                                  ▼
┌─────────────┐           ┌─────────────┐                    ┌─────────────┐
│ MCP Servers │◀─────────▶│  PostgreSQL │                    │  Responses  │
│  & Tools    │           │  Redis      │                    │  (filtered) │
└─────────────┘           │  Celery     │                    └─────────────┘
                          └─────────────┘
```

## Request Flow

1. **Ingress** — Agent/user request enters via AI Gateway (OpenAI/Gemini compatible)
2. **Classification** — Data classified, PII/secrets/financial info detected
3. **Policy Evaluation** — OPA-backed governance policies applied
4. **Routing** — LLM Router selects approved model based on rules
5. **MCP Governance** — Tool calls inspected and governed
6. **Egress** — Response inspected for leakage, masked, audited
7. **Observability** — Full trace exported via OpenTelemetry

## Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | Next.js 16 | Enterprise UI, dashboard, module interfaces |
| API Gateway | FastAPI | REST API, auth, tenant scoping |
| AI Proxy | FastAPI (Phase 2) | OpenAI/Gemini compatible gateway |
| Policy Engine | OPA (Phase 2) | Policy evaluation |
| Job Queue | Celery + Redis | Async processing, audit ingestion |
| Database | PostgreSQL | Tenant-scoped persistent storage |
| Cache | Redis | Session, rate limiting, pub/sub |
| Observability | OpenTelemetry | Traces, metrics, logs |

## Multi-Tenancy

Every database object includes `tenant_id`. JWT tokens carry tenant context. API middleware enforces tenant isolation at the query level.

### Hierarchy

```
Tenant
├── Organization
│   ├── Business Unit
│   │   ├── Department
│   │   │   └── User (with Role)
```

## Deployment

- **Development:** Docker Compose (frontend + backend + postgres + redis)
- **Production:** Kubernetes with Helm charts (Phase 5)
- **Air-Gap:** Offline bundle with local LLM support (Phase 5)
