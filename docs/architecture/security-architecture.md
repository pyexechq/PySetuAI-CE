# Security Architecture

## Authentication

- JWT access tokens with configurable expiry (default 60 min)
- Token payload: `sub` (user ID), `tenant_id`, `role`, `exp`
- Password hashing via bcrypt (passlib)
- Future: refresh tokens, SSO/OIDC integration — see [oidc-sso-design.md](./oidc-sso-design.md)

## Authorization

### RBAC (Role-Based Access Control)

Six predefined roles with hierarchical permissions (see backend-architecture.md).

### ABAC (Attribute-Based Access Control)

Open Policy Agent (OPA) evaluates gateway ABAC rules after regex/DLP inspection:

- Policy package: `pysetu.gateway` (`deploy/opa/policies/gateway.rego`)
- Evaluated attributes: user role, auth type (JWT vs client key), policy bundle, routed model, PII/region, risk level, UTC hour
- Config: `OPA_ENABLED`, `OPA_BASE_URL`, `OPA_FAIL_OPEN` (fail-open in dev, fail-closed in production)
- Dry-run: `POST /api/v1/security/opa/evaluate`
- Status: `GET /api/v1/security/opa/status`

Planned extensions:
- User attributes (role, department)
- Resource attributes (data classification, MCP risk score)
- Environmental attributes (time, IP, air-gap status)

## Data Protection

- All API communication over TLS in production
- Tenant data isolation at database query level
- PII detection and redaction pipeline (Phase 2)
- Secrets stored in Hashicorp Vault (Phase 5), not in code

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Prompt injection | AI Security Center detection + policy block |
| Data exfiltration | Output inspection + DLP policies |
| Cross-tenant access | JWT tenant_id enforcement + query filtering |
| MCP tool abuse | MCP governance trust/risk scoring |
| Credential leakage | Secret detection + Vault integration |
| JWT theft | Short expiry, HTTPS only, future refresh rotation |

## Compliance

Framework tracking for GDPR, HIPAA, SOC2, ISO27001, NIST built into Compliance Center module.

## Security Headers (Production)

- Content-Security-Policy
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Strict-Transport-Security

## Known Security Debt

- JWT secret uses dev default (KI-005)
- Redis-backed rate limiting on auth endpoints (S6-04)
- No RBAC enforcement on API routes yet
- No audit logging of auth events yet
