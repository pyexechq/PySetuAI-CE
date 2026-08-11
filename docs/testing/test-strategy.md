# PySetu AI — Test Strategy

**Version:** 1.0  
**Last Updated:** Aug 11, 2026  
**Owner:** Principal QA & Validation Agent

---

## Purpose

Define the quality assurance approach for PySetu AI across functional, security, compliance, performance, and multi-tenant validation. Documentation is the source of truth; implementation is validated against `docs/architecture/`, `docs/security/`, and `docs/api/`.

---

## Test Pyramid

```
                    ┌─────────────┐
                    │  E2E / UAT  │  Playwright (planned)
                   ┌┴─────────────┴┐
                   │  Integration  │  pytest + httpx (partial)
                  ┌┴───────────────┴┐
                  │  Unit / Service │  pytest (44 tests), Vitest (none)
                 ┌┴─────────────────┴┐
                 │  Static Analysis   │  ruff, eslint, TypeScript
                 └───────────────────┘
```

---

## Test Layers

### 1. Static Analysis & Build Verification

| Layer | Tool | Scope | Status |
|-------|------|-------|--------|
| Backend lint | ruff | Python style/errors | Planned CI |
| Frontend lint | eslint | React/TS | Available |
| Frontend build | `next build` | 33 routes compile | **Passing** |
| TypeScript | `tsc` | Type safety | **Passing** |

### 2. Backend Unit & Service Tests

| Module | Tool | Coverage | Status |
|--------|------|----------|--------|
| Policy engine | pytest | Rule evaluation, region/PII conditions | **12 tests** |
| Security scan | pytest | Injection, exfiltration detection | **3 tests** |
| Rate limiting | pytest | Auth paths, IP extraction, limits | **4 tests** |
| OIDC auth | pytest | PKCE, role mapping | **3 tests** |
| SIEM export | pytest | CEF, NDJSON, Elastic formats | **4 tests** |
| OPA service | pytest | Input builder | **1 test** |
| Tenant branding/site | pytest | Subdomain, display name | **8 tests** |
| Vault/OIDC config | pytest | Role mapping, JWT secret check | **3 tests** |
| Alert webhooks | pytest | Slack/ServiceNow payloads | **2 tests** |
| Dashboard trends | pytest | Percent change math | **3 tests** |
| Platform tenants | pytest | Slug validation only | **8 tests** |

**Total:** 44 tests, all passing (Aug 11, 2026).

### 3. Backend Integration Tests (Planned / Missing)

| Area | Priority | Status |
|------|----------|--------|
| Auth login/logout flow | P0 | **Not implemented** |
| JWT validation on protected routes | P0 | **Not implemented** |
| Cross-tenant data isolation | P0 | **Not implemented** |
| Policy CRUD API | P1 | **Not implemented** |
| Gateway chat completions + audit | P1 | **Not implemented** |
| MCP server CRUD + health | P1 | **Not implemented** |
| Compliance snapshot API | P2 | **Not implemented** |
| OIDC callback flow | P2 | **Not implemented** |

### 4. Frontend Tests

| Type | Tool | Status |
|------|------|--------|
| Unit (utils, stores) | Vitest | **Not implemented** |
| Component | Vitest + Testing Library | **Not implemented** |
| E2E | Playwright | **Not implemented** |

### 5. Security Testing

| Category | Method | Frequency |
|----------|--------|-----------|
| Prompt injection | Automated (security scan service) + manual attack strings | Every sprint |
| Data exfiltration | Automated (security scan) + manual | Every sprint |
| Jailbreak | Manual attack simulation via Studio/Gateway | Every sprint |
| RBAC privilege escalation | Manual + planned integration tests | Every sprint |
| Cross-tenant access | Manual + planned integration tests | Every release |
| API abuse / rate limiting | Unit tests + manual | Every sprint |
| Dependency vulnerabilities | `pip audit` / `npm audit` | Pre-release |

### 6. Compliance Testing

| Framework | Method | Status |
|-----------|--------|--------|
| GDPR | Control panel review + snapshot export | Heuristic scoring only |
| HIPAA | Control panel review | Heuristic scoring only |
| SOC 2 | Control panel review | Heuristic scoring only |
| ISO 27001 | Control panel review | Heuristic scoring only |
| NIST AI RMF | Control panel review | Heuristic scoring only |

Compliance scores are **advisory/heuristic**, not certified attestation.

### 7. Performance Testing

| Target | Threshold | Method |
|--------|-----------|--------|
| Dashboard load | < 2 sec | Manual / k6 (planned) |
| API response (p95) | < 500 ms | Manual / k6 (planned) |
| Policy evaluation | < 100 ms | Unit benchmark (planned) |
| Audit search | < 2 sec | Manual (planned) |

### 8. Regression Testing

Full regression suite runs before each release gate. Current regression scope is limited to:
- Backend unit tests (44)
- Frontend production build
- Manual smoke of critical paths

---

## Environments

| Environment | Purpose | Data |
|-------------|---------|------|
| Local (Docker Compose) | Dev + QA validation | Demo seed data |
| CI (planned) | Automated gates | Ephemeral test DB |
| Staging (planned) | Pre-production UAT | Anonymized data |
| Production | Release | Real tenant data |

---

## Defect Severity Classification

| Severity | Definition | Release Block |
|----------|------------|---------------|
| S1 | Security issue, data leakage, cross-tenant access | **Yes** |
| S2 | Core feature broken | **Yes** |
| S3 | Functional issue, workaround exists | No (track) |
| S4 | Cosmetic / minor UX | No |

---

## Release Gate Criteria

A release may only be approved when:

- [ ] Critical defects (S1) = 0
- [ ] Security defects (S1) = 0
- [ ] Regression suite passed
- [ ] Performance targets met (or waived with sign-off)
- [ ] Documentation updated
- [ ] Handoff notes updated
- [ ] Test evidence generated

**Current release decision:** **NOT APPROVED** — see [release-readiness.md](./release-readiness.md).

---

## Tooling Roadmap

| Sprint | Deliverable |
|--------|-------------|
| S6-09 | Penetration test prep checklist | Done |
| S7+ | pytest integration tests with testcontainers |
| S7+ | Vitest unit tests for frontend stores/utils |
| S8+ | Playwright E2E for auth + dashboard + policy CRUD |
| S9+ | k6 performance baseline suite |
| M5 | Full CI pipeline with all layers |
