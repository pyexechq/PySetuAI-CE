# PySetu AI — Test Results

**Test Cycle:** QA-006 (UI Polish / AG Grid Theme Alignment) — **PASSED**  
**Completed:** Aug 12, 2026

### Audit Explorer Table Dark Theme Alignment

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| AG Grid theme class | Added `ag-theme-quartz-dark` |
| CSS Variable Fix | Fixed invalid `hsl(var(...))` wrappers in `globals.css` to `var(...)` for `--card`, `--foreground`, `--muted`, `--border`, `--secondary` |
| Next.js frontend TypeScript compilation | **Passed (0 errors)** |
| Open defects | 0 blocking |

---

**Test Cycle:** QA-005 (Sprint 10 Exit / Custom Intents BL-062 Validation) — **PASSED**  
**Completed:** Aug 12, 2026

### Sprint 10 Final Test Results (BL-061 & BL-062 Complete)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (backend container) | **163 passed**, 0 failed (4 new test cases covering Custom Intents & Scan Engine) |
| Next.js frontend TypeScript compilation | **Passed (0 errors)** |
| Open defects | 0 blocking for Sprint 10 |
| Milestone Status | **Sprint 10 Complete (Prompt Store & Custom Intents APPROVED)** |

---

**Test Cycle:** QA-004 (Sprint 10 / Prompt Store BL-061 Validation) — **PASSED**  
**Completed:** Aug 12, 2026

### Sprint 10 Test Results (BL-061 Managed Prompt Store & Gateway Ingress Injection)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (backend container) | **159 passed**, 0 failed (7 new test cases covering Prompt Templates & Ingress Injection) |
| Next.js frontend TypeScript compilation | **Passed (0 errors)** |
| Open defects | 0 blocking for Sprint 10 |
| Completed Tasks | **S10-01, S10-02, S10-03 (BL-061 Complete)** |

---

**Test Cycle:** QA-003 (Sprint 9 Exit / M8 Milestone) — **PASSED**  
**Completed:** Aug 12, 2026

### Sprint 9 Test Results (M8 Gateway Parity)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (backend container) | **152 passed**, 0 failed |
| Next.js frontend build | **Compiled successfully** (41 static/dynamic pages) |
| Open defects | 0 blocking for Sprint 9 |
| Release milestone | **M8 — Gateway Pipeline Parity APPROVED** |

---

**Test Cycle:** QA-001  
**Date:** Aug 11, 2026  
**Environment:** Local (Windows 10, Python 3.12.10, Node.js/Next.js 16.3.0)  
**Executed By:** Principal QA & Validation Agent

---

## Summary (QA-001 baseline)

| Category | Total | Pass | Fail | Blocked | Not Tested |
|----------|-------|------|------|---------|------------|
| Backend unit tests | 44 | 44 | 0 | 0 | — |
| Frontend build | 1 | 1 | 0 | 0 | — |
| Feature validation (matrix) | 72 | 28 | 5 | 4 | 35 |
| Security tests | 21 | 6 | 1 | 1 | 13 |
| Performance tests | 4 | 0 | 0 | 0 | 4 |

**Overall cycle result:** **INCOMPLETE** — significant gaps in integration, E2E, and performance testing.

---

## Automated Test Results

### Backend — pytest

```
Platform: win32 — Python 3.12.10, pytest 9.1.1
Collected: 44 items
Result: 44 passed in 2.03s
Exit code: 0
```

| Test File | Tests | Result |
|-----------|-------|--------|
| test_alert_webhooks.py | 2 | PASS |
| test_dashboard_trends.py | 3 | PASS |
| test_oidc_auth.py | 3 | PASS |
| test_opa_service.py | 1 | PASS |
| test_platform_tenants.py | 8 | PASS |
| test_policy_engine.py | 5 | PASS |
| test_rate_limit.py | 4 | PASS |
| test_security_scan.py | 3 | PASS |
| test_siem_export.py | 4 | PASS |
| test_tenant_branding.py | 5 | PASS |
| test_tenant_site.py | 3 | PASS |
| test_vault_oidc.py | 3 | PASS |

### Frontend — next build

```
Next.js 16.3.0 (Turbopack)
Compiled successfully in 7.5s
TypeScript: finished in 15.5s
33 static/dynamic routes generated
Exit code: 0
```

Warnings (non-blocking):
- `middleware` file convention deprecated (Next.js 16 migration to proxy)
- package-lock.json outside git repo root

---

## Feature Validation Results (QA-001)

### Passed (verified via code review + unit tests + build)

- Policy engine: region/PII conditions, injection blocking, audit status normalization
- Security scan: injection detection, exfiltration detection, safe text allowance
- Rate limiting: auth path inclusion, forwarded IP, allow/block thresholds
- OIDC: PKCE generation, role mapping from groups
- SIEM export: CEF, NDJSON, Elastic bulk format correctness
- Tenant branding: display name resolution, public branding shape
- Tenant site: subdomain extraction, entry mode validation
- Vault/OIDC config: role mapping validation, insecure JWT secret detection
- Alert webhooks: Slack/ServiceNow payload construction
- Dashboard trends: percent change calculations
- Platform tenant slug validation
- All 33 frontend routes compile and render
- ~120 backend API endpoints registered with RBAC guards
- JWT tenant_id mismatch rejection in `get_current_user`
- Frontend auth: middleware + AuthGuard + RBAC route matrix

### Failed

| ID | Module | Finding |
|----|--------|---------|
| MCP-005 | MCP Governance | Tool invoke has no policy gate — `invoke_mcp_server_tool` calls `invoke_mcp_tool` directly without policy evaluation |
| MCP-009 | MCP Governance | No audit log entry created on MCP tool invoke |
| STU-005 | Studio | MCP Simulator uses client-side mock, not live `tools/invoke` API |
| SEC-007 | Security Center | Alert webhooks have CRUD + manual test only; no auto-dispatch on policy violations |
| AUTHZ-* / MT-* | Multi-Tenant | No integration tests for cross-tenant isolation despite app-layer scoping |

### Blocked

| ID | Module | Reason |
|----|--------|--------|
| LLM-006–009 | LLM Router | `gateway_mock_mode=True` default; no upstream API keys configured |
| AUTH-005 | Authentication | MFA not implemented |
| SEC-005 | Security Center | `opa_enabled=False`, `opa_fail_open=True` by default |

### Not Tested (deferred to QA-002+)

- Dashboard date range filters, export, empty state, performance
- Policy cloning, versioning, flow canvas edge cases
- LLM model failover, cost routing, live upstream verification
- Audit search/filter/export manual verification
- Compliance evidence accuracy
- Full auth flow (login/logout/session expiry/OIDC)
- RBAC privilege escalation attempts
- Performance benchmarks (dashboard, API, policy eval, search)

---

## Documentation vs Implementation Gaps

| Document | Documented State | Actual State | Verdict |
|----------|-----------------|--------------|---------|
| docs/testing/README.md | "No automated tests yet" | 44 pytest tests passing | **Doc stale** |
| docs/handoffs/security-agent.md | "No rate limiting, no RBAC on API" | Rate limiting + RBAC implemented | **Doc stale** |
| docs/handoffs/backend-agent.md | "Stub endpoints, no DB" | Full CRUD, migrations, 120 endpoints | **Doc stale** |
| docs/progress/known-issues.md KI-004 | "Module pages use mock data" | Live API wired | **Resolved, doc stale** |
| docs/progress/known-issues.md KI-005 | "JWT secret dev default" | Vault integration done (S6-01), prod guard added | **Partially resolved** |
| docs/api/README.md | Lists only 4 endpoints | ~120 endpoints implemented | **Doc stale** |
| docs/security/README.md checklist | Rate limiting unchecked | Implemented (S6-04) | **Doc stale** |

---

## Evidence Artifacts

| Artifact | Location |
|----------|----------|
| pytest output | This document (Aug 11, 2026 run) |
| next build output | This document (Aug 11, 2026 run) |
| Defect log | [defect-log.md](./defect-log.md) |
| Security findings | [security-findings.md](./security-findings.md) |
| Release readiness | [release-readiness.md](./release-readiness.md) |
