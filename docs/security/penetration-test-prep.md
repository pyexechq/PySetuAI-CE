# Penetration Test Preparation Checklist

PySetu AI — pre-engagement hardening and evidence collection for S6-09.

## Scope

- Tenant web UI (`frontend/`)
- Platform operator portal (`/platform`, `/platform/ops`)
- REST API (`/api/v1`, OpenAI-compatible gateway)
- Auth flows (local login, OIDC, tenant invites)
- Policy engine (OPA) and audit pipeline

## Authentication & session

- [ ] Verify JWT expiry and refresh behavior under clock skew
- [ ] Confirm platform routes reject non-`platform_admin` roles (403)
- [ ] Test tenant invite tokens: expiry, single-use acceptance, invalid token handling
- [ ] Validate auth rate limiting on `/auth/login` and `/auth/accept-invite`
- [ ] Review OIDC state/nonce validation and redirect URI allow-list

## Authorization (RBAC / ABAC)

- [ ] Horizontal privilege: tenant A cannot access tenant B resources by ID tampering
- [ ] Client API keys scoped to tenant; gateway rejects cross-tenant bundle IDs
- [ ] Feature flags enforced server-side (QA, Reports, Compatibility Center, Studio)
- [ ] Platform feature PATCH cannot be invoked by tenant admins

## Input validation & injection

- [ ] SQLi on list/filter endpoints (audit, reports, governance)
- [ ] XSS in branding fields, policy names, audit actor fields (stored/reflected)
- [ ] SSRF via custom LLM provider `endpoint_url` and MCP server URLs
- [ ] Prompt injection paths documented (gateway policy dry-run vs production)

## Secrets & crypto

- [ ] API keys and provider secrets not returned in GET responses
- [ ] `.env` / Vault paths excluded from repo; production JWT from Vault
- [ ] Invite tokens are high-entropy, not guessable; passwords hashed (bcrypt)

## Gateway & UAG

- [ ] `pysetu` debug block only with `?mode=debug`
- [ ] Client response protocol override order: mapping → API key → tenant
- [ ] Streaming responses do not leak upstream errors with stack traces

## Infrastructure

- [ ] `/health` reports DB + OPA dependency status (no sensitive data)
- [ ] CORS origins restricted in production
- [ ] Docker images run as non-root; health checks configured
- [ ] Dependency scan (Python + Node) in CI

## Logging & evidence

- [ ] Audit log coverage for gateway block/allow, policy changes, platform tenant CRUD
- [ ] SIEM connector export format reviewed for PII redaction
- [ ] Operator SLA dashboard (`/platform/ops`) accessible only to platform admins

## Deliverables for testers

1. Architecture diagram (tenant vs platform vs gateway)
2. Test accounts: platform admin, tenant admin, developer, auditor
3. Demo API keys and sample curl commands for gateway
4. List of out-of-scope systems (external LLM providers, IdP)

## Sign-off

| Role | Name | Date |
|------|------|------|
| Engineering | | |
| Security | | |
| Product | | |
