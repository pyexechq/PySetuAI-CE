# Data Model

## Core Entities

### Tenant

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| name | VARCHAR(255) | Display name |
| slug | VARCHAR(100) | Unique URL identifier |
| is_active | BOOLEAN | Soft disable |
| created_at | TIMESTAMPTZ | Auto |

### User

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | Primary key |
| tenant_id | UUID | FK → tenants.id |
| email | VARCHAR(255) | Unique per tenant |
| name | VARCHAR(255) | Display name |
| hashed_password | VARCHAR(255) | bcrypt |
| role | VARCHAR(50) | RBAC role enum |
| is_active | BOOLEAN | Soft disable |
| created_at | TIMESTAMPTZ | Auto |

## Planned Entities (Phase 2+)

### Policy
- id, tenant_id, name, type, definition (JSON), version, status, created_by

### LLMProvider
- id, tenant_id, name, provider_type, endpoint, api_key_ref, is_active

### RoutingRule
- id, tenant_id, name, priority, conditions (JSON), target_provider_id

### MCPServer
- id, tenant_id, name, endpoint, trust_score, risk_score, status

### AuditLog
- id, tenant_id, request_id, agent_id, model, action, risk_level, status, tokens, timestamp

### PolicyViolation
- id, tenant_id, audit_log_id, policy_id, severity, details (JSON)

## Relationships

```
Tenant 1──N User
Tenant 1──N Policy
Tenant 1──N LLMProvider
Tenant 1──N MCPServer
Tenant 1──N AuditLog
AuditLog 1──N PolicyViolation
```

## Indexing Strategy

- All tables: index on `tenant_id`
- AuditLog: composite index on `(tenant_id, timestamp DESC)`
- User: unique index on `(tenant_id, email)`
