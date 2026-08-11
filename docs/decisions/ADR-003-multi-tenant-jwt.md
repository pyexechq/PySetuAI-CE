# ADR-003: Multi-Tenant JWT Scoping

## Status

Accepted

## Context

HelixGuard AI is a multi-tenant SaaS platform. Every API request and database query must be scoped to a tenant. We need an authentication mechanism that carries tenant context.

## Decision

Embed `tenant_id` and `role` in JWT access tokens. API middleware extracts and enforces tenant scope on all queries.

## Alternatives Considered

1. **Tenant ID in header only** — Rejected; headers can be spoofed without cryptographic binding to identity.
2. **Separate tenant resolution from subdomain** — Planned as supplementary mechanism; JWT remains source of truth for API auth.
3. **Session-based auth with server-side tenant** — Rejected for API-first architecture and future mobile/agent clients.

## Consequences

- Every token is bound to exactly one tenant
- Cross-tenant access requires platform_admin role with explicit override
- Token refresh must preserve tenant context
- Future: support tenant switching via new token issuance
