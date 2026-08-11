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
  "service": "HelixGuard AI",
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
