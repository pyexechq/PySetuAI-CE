# HelixGuard AI — Regression Report

**Test Cycle:** QA-001  
**Date:** Aug 11, 2026  
**Baseline:** Initial validation (no prior regression baseline)  
**Executed By:** Principal QA & Validation Agent

---

## Regression Scope

This is the **initial regression baseline** for HelixGuard AI. No prior test cycle exists for comparison. Future cycles will diff against QA-001 results.

### Automated Regression

| Suite | Tests | Pass | Fail | Skip | Duration |
|-------|-------|------|------|------|----------|
| Backend pytest | 44 | 44 | 0 | 0 | 2.03s |
| Frontend build | 1 | 1 | 0 | 0 | 42.2s |

### Manual Smoke (Code Review Based)

| Area | Check | Result |
|------|-------|--------|
| Auth middleware | Next.js middleware protects routes | Pass |
| Auth guard | Client AuthGuard + RBAC route matrix | Pass |
| Platform guard | PlatformAuthGuard restricts `/platform/*` | Pass |
| API router | 16 route modules, ~120 endpoints | Pass |
| RBAC guards | Permission checks on write/admin routes | Pass (code review) |
| Tenant scoping | `tenant_id` in governance queries | Pass (code review) |
| JWT mismatch | Token tenant ≠ user tenant → 403 | Pass (code review) |
| Policy engine | Built-in rules + tenant rules + DLP | Pass (unit tests) |
| Gateway audit | Auto-audit on chat completions | Pass (code review) |
| Celery tasks | Reports, audit ingest, SIEM export, rebalance | Pass (code review) |

---

## Regression Results by Module

| Module | Status | Regressions | Notes |
|--------|--------|-------------|-------|
| Executive Dashboard | **Pass** | 0 | Build + API wiring verified |
| Policy Studio | **Pass** | 0 | CRUD endpoints + unit tests |
| LLM Router | **Pass** | 0 | CRUD endpoints exist; mock mode default |
| MCP Governance | **Partial** | 0 new | Pre-existing gaps (no policy gate on invoke) |
| Audit Explorer | **Pass** | 0 | Export + SIEM endpoints verified |
| Studio | **Partial** | 0 new | MCP Simulator mock is pre-existing |
| Compliance Center | **Pass** | 0 | Snapshot API verified |
| Security Center | **Pass** | 0 | Scan unit tests pass |
| AI Gateway | **Pass** | 0 | Gateway service + audit verified |
| Settings | **Pass** | 0 | All settings sub-routes build |
| Platform Admin | **Pass** | 0 | Tenant provisioning API verified |
| Auth / OIDC | **Pass** | 0 | PKCE + role mapping unit tests |

---

## Critical Regression Check

| Gate | Requirement | Result |
|------|-------------|--------|
| No S1 regressions | 0 new S1 defects | **Pass** (no prior baseline; S1 defects are pre-existing) |
| No S2 regressions | 0 new S2 defects | **Pass** (no prior baseline) |
| Build succeeds | Frontend + backend compile | **Pass** |
| Unit tests pass | 44/44 | **Pass** |
| Security controls intact | Injection/exfiltration detection | **Pass** |

---

## Known Pre-Existing Issues (Not Regressions)

These issues existed before QA-001 and are tracked in the defect log:

- DEF-001: MCP tool invoke lacks policy gate
- DEF-002: MCP tool invoke not audited
- DEF-003: Studio MCP Simulator is mocked
- DEF-004: Alert webhooks not event-driven
- DEF-005: No tenant isolation integration tests
- DEF-006: OPA disabled by default

---

## Regression Test Gaps

The following areas have **no automated regression coverage**:

1. Authentication flow (login → JWT → protected route → logout)
2. Cross-tenant data access prevention
3. RBAC permission denial (403 on unauthorized actions)
4. Gateway chat completion end-to-end (policy → route → audit)
5. Policy CRUD lifecycle (create → activate → evaluate → deactivate)
6. MCP server lifecycle (register → health → discover → invoke)
7. Compliance snapshot accuracy
8. Frontend component rendering and interaction
9. OIDC authorization code flow
10. Rate limiting under load

---

## Recommendation

**Regression status: BASELINE ESTABLISHED**

No regressions detected (first cycle). However, regression coverage is insufficient for release confidence. Priority actions:

1. Add integration test suite covering auth + tenant isolation (blocks release)
2. Add Playwright E2E for critical user journeys
3. Establish performance regression baseline with k6

**Next regression cycle:** QA-002 (target: Sprint 7)
