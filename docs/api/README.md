# API Reference

**Base URL:** `http://localhost:8000`  
**API Prefix:** `/api/v1`

## Health

### GET /health

Returns service health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "PySetu AI",
  "version": "0.1.0"
}
```

## Authentication

### POST /api/v1/auth/login

Authenticate user and receive JWT token.

**Request:**
```json
{
  "email": "admin@acme.com",
  "password": "string",
  "tenant_slug": "acme"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

### GET /api/v1/auth/me

Get current authenticated user.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "id": "usr-001",
  "email": "admin@acme.com",
  "name": "Admin User",
  "role": "tenant_admin",
  "tenant_id": "tenant-acme"
}
```

## Tenants

### GET /api/v1/tenants/current

Get current tenant context.

**Response:**
```json
{
  "id": "tenant-acme",
  "name": "Acme Corporation",
  "slug": "acme"
}
```

## Dashboard

### GET /api/v1/dashboard/metrics

Get executive dashboard KPI metrics.

**Response:**
```json
{
  "total_requests": 1200000,
  "blocked_requests": 12421,
  "pii_redactions": 34123,
  "policy_violations": 1203,
  "mcp_violations": 823,
  "cost_savings": 78542.0,
  "compliance_score": 89.0
}
```

## Planned Endpoints (Phase 2+)

- `POST /api/v1/gateway/chat/completions` — OpenAI-compatible proxy
- `GET/POST /api/v1/policies` — Policy CRUD
- `GET/POST /api/v1/llm/providers` — LLM provider registry
- `GET/POST /api/v1/mcp/servers` — MCP server registry
- `GET /api/v1/audit/logs` — Audit log search

## Compliance & governance (Aug 15)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/compliance/iac-evidence/config` | Tenant IaC scanner config |
| PUT | `/compliance/iac-evidence/config` | Save scan paths + checks (admin) |
| POST | `/compliance/iac-evidence/config/reset` | Reset IaC defaults |
| GET | `/compliance/iac-evidence/scan` | Run IaC evidence scan |
| GET | `/compliance/data-movement-policy` | Tenant OPA data-movement policy |
| PUT | `/compliance/data-movement-policy` | Save policy (admin) |
| POST | `/compliance/data-movement-policy/reset` | Reset movement defaults |
| GET | `/rag-gateway/evidence` | List GenAI evidence bundles |
| GET | `/rag-gateway/evidence/{id}/export` | Export evidence JSON |
| POST | `/rag-gateway/demo-events` | Seed demo RAG events (debug) |
| GET | `/security/vault/status` | Vault connectivity + JWT bootstrap status |
| POST | `/reports/{report_id}/preview` | Report preview data for modal |
| GET/POST | `/help/chat` | In-app help assist |

Full UX map: [aug-15-compliance-ux-update.md](../progress/aug-15-compliance-ux-update.md)
