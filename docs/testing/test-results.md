# PySetu AI — Test Results

**Test Cycle:** QA-028 (Sprint 15 / REST-to-MCP spec proxy BL-083) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 15 BL-083 Test Results (REST-to-MCP auto-proxy backend)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (`test_mcp_spec_proxy.py` + MCP catalog/url-filter/tool-risk regressions) | **29 passed**, 0 failed |
| API surface | Permission-protected `POST /mcp/servers/parse-spec` |
| Coverage | OpenAPI 3.x, Swagger 2.0 host/basePath, Postman v2 folders, GraphQL SDL query/mutation, error paths |
| Tool naming | Matches client wizard (`to_tool_name`) |
| Completed Tasks | **BL-083 (backend spec-proxy endpoint)** |

---

**Test Cycle:** QA-027 (Sprint 14 / Gateway SLA dashboard BL-078) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 14 S14-05 Test Results (BL-078 gateway SLA dashboard)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (`test_sla_service.py` + telemetry/regional regressions) | **18 passed**, 0 failed |
| TypeScript (`tsc --noEmit`) | **0 errors** |
| API surface | Permission-protected `GET /telemetry/sla` |
| Coverage | Availability, error rate, p50/p95/p99 latency, gateway overhead, active providers, US fallback, pooling status |
| Frontend | Gateway SLA card added to Monitoring Overview with 30-second refresh |
| Pooling | Shared application HTTP client with reuse counters and shutdown cleanup |
| Completed Tasks | **S14-05 (BL-078)** |

**Test Cycle:** QA-026 (Sprint 14 / Regional routing GA BL-077) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 14 S14-04 Test Results (BL-077 regional routing GA)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (`test_regional_routing_service.py` + regional adapters + gateway) | **11 passed**, 0 failed |
| Coverage | US/EU/India policy-bundle mapping, provider-native endpoints, US fallback, Bedrock and Vertex gateway branches |
| Routing behavior | Active policy bundle now supplies the region to both regional adapters; no-bundle requests default to US |
| Open defects | 0 blocking for S14-04 |
| Completed Tasks | **S14-04 (BL-077)** |

**Test Cycle:** QA-025 (Sprint 14 / Claude compliance sync BL-081) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 14 S14-03 Test Results (BL-081 Claude compliance sync)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (`test_claude_compliance_service.py` + compliance/DLP regressions) | **17 passed**, 0 failed |
| Coverage | Organization/user/chat aggregation, PHI/PCI/financial DLP findings, clean-chat control, tenant-scoped audit evidence path |
| API surface | Permission-protected `POST /compliance/claude/sync` |
| Open defects | 0 blocking for S14-03 |
| Scope note | Normalized sync adapter is complete; live Anthropic credential management and scheduled provider pull remain deployment work |
| Completed Tasks | **S14-03 (BL-081)** |

**Test Cycle:** QA-024 (Sprint 14 / PHI-PCI-financial classifiers BL-082) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 14 S14-02 Test Results (BL-082 data protection classifiers)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (`test_data_protection_service.py` + gateway/compliance regressions) | **14 passed**, 0 failed |
| Coverage | PHI keyword patterns, PCI card numbers, financial account terms, redaction, benign financial language |
| API surface | Permission-protected `POST /data-protection/scan` |
| Open defects | 0 blocking for S14-02 |
| Scope note | Deterministic regex classifiers; regulated-data certification and ML recall benchmarking remain future work |
| Completed Tasks | **S14-02 (BL-082)** |

**Test Cycle:** QA-023 (Sprint 14 / Red-team baseline BL-080) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 14 S14-01 Test Results (BL-080 red-team testing suite)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (`test_red_team_service.py` + QA/security regressions) | **11 passed**, 0 failed |
| Coverage | Five detector-backed adversarial cases plus one benign control; aggregate scoring; CSV export |
| API surface | Authenticated `GET /qa/red-team/run`; JSON/CSV `GET /qa/red-team/export` |
| Open defects | 0 blocking for S14-01 |
| Completed Tasks | **S14-01 (BL-080)** |

**Test Cycle:** QA-022 (Sprint 13 / Alert Webhooks + Live Ops Panel) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 13 S13-05/S13-06 Test Results (BL-075 latency/outage alerts · BL-076 live ops panel)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (`test_alert_webhooks.py` + telemetry + observability) | **20 passed**, 0 failed |
| TypeScript (`tsc --noEmit`) | **0 errors** |
| Live smoke | App healthy; `/telemetry/operations` live data; alert titles for `gateway.latency.high` / `gateway.upstream.outage` |
| Coverage | Latency (30s threshold) + outage alert dispatch from non-stream & stream paths; live ops panel (requests/tokens/p50/blocks/recent blocked) |
| Open defects | 0 blocking for S13-05/S13-06 |
| Completed Tasks | **S13-05 (alert actions + gateway wiring), S13-06 (telemetry ops card in Monitoring Overview)** |

---

**Test Cycle:** QA-021 (Sprint 13 / Telemetry Facade BL-076) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 13 S13-04 Test Results (BL-076 Telemetry facade `/telemetry/*`)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (`test_telemetry_facade.py` + related suites) | **21 passed**, 0 failed |
| Live smoke | `/telemetry/summary` `/operations` `/security` `/traces` all 200 with auth; 401 without |
| Coverage | Summary (events/latency/tokens/cost), operations panel (requests/tokens/p50/blocks), security analytics, trace summaries |
| Open defects | 0 blocking for S13-04 |
| Completed Tasks | **S13-04 (telemetry facade schemas, service aggregation, `/telemetry/*` routes, RBAC)** |

---

**Test Cycle:** QA-020 (Sprint 13 / Trace Replay BL-074) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 13 S13-03 Test Results (BL-074 OTel trace replay)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (`test_trace_replay.py` + observability traces) | **7 passed**, 0 failed |
| TypeScript (`tsc --noEmit`) | **0 errors** |
| Coverage | Stage-by-stage spans from audit/UAG/failover, OTel trace id, detail API, Monitoring + Audit Explorer UI |
| Open defects | 0 blocking for S13-03 |
| Completed Tasks | **S13-03 (trace_replay_service, `/observability/traces/{id}`, timeline UI)** |

---

**Test Cycle:** QA-019 (Sprint 13 / Request Log Retention BL-073) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 13 S13-02 Test Results (BL-073 Full request/response log retention)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (`test_request_log_retention.py` + cost analytics) | **5 passed**, 0 failed |
| TypeScript (`tsc --noEmit`) | **0 errors** |
| Coverage | Payload serialization, guardrail events, truncation, gateway capture, audit API + explorer UI |
| Open defects | 0 blocking for S13-02 |
| Completed Tasks | **S13-02 (audit_log_bodies table, retention settings, purge, request log panel)** |

---

**Test Cycle:** QA-018 (Sprint 13 / Cost Analytics BL-072) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 13 S13-01 Test Results (BL-072 Per-user/team/model cost analytics)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (`test_cost_analytics.py`) | **2 passed**, 0 failed |
| TypeScript (`tsc --noEmit`) | **0 errors** |
| Coverage | Audit `usage_metadata` aggregation by model/user/team, daily trend, dashboard API + card |
| Open defects | 0 blocking for S13-01 |
| Completed Tasks | **S13-01 (cost analytics service, `/dashboard/cost-analytics`, dashboard card, overview LLM usage from audit)** |

---

**Test Cycle:** QA-017 (Sprint 12 / URL Filters BL-071) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 12 S12-07 Test Results (BL-071 Web Search + URL Filters)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (URL filters + Sprint 12 MCP suites) | **59 passed**, 0 failed |
| Coverage | Denylist/allowlist, private IP block, web-search gate, vendor hook, multiplex + invoke enforcement |
| Open defects | 0 blocking for S12-07 |
| Completed Tasks | **S12-07 (URL filter API, vendor hooks, gateway enforcement, Governance UI)** |

---

**Test Cycle:** QA-016 (Sprint 12 / MCP Portal BL-070) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 12 S12-06 Test Results (BL-070 Self-service MCP Portal)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (portal + related MCP suites) | **51 passed**, 0 failed |
| Coverage | Portal visibility, connection status, per-user token connect, gateway token resolution |
| Open defects | 0 blocking for S12-06 |
| Completed Tasks | **S12-06 (portal API, per-user connections, Governance admin card, `/mcp-portal` UI)** |

---

**Test Cycle:** QA-015 (Sprint 12 / Agent MCP Toggles BL-069) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 12 S12-05 Test Results (BL-069 Agent Detection + Per-agent MCP)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (agent + related MCP suites) | **43 passed**, 0 failed |
| Coverage | UA/metadata classification, tenant toggles, per-server allowlists, gateway server filter |
| Open defects | 0 blocking for S12-05 |
| Completed Tasks | **S12-05 (agent settings API, detection probe, gateway + multiplex filter, Governance UI)** |

---

**Test Cycle:** QA-014 (Sprint 12 / Tool Risk Taxonomy BL-068) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 12 S12-04 Test Results (BL-068 Read / Write / Destructive + Auto-hide)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (tool risk + multiplex + catalog + oauth + dynamic tools) | **35 passed**, 0 failed |
| Coverage | Name/description classification, explicit hide, auto-hide destructive, policy merge overrides |
| Open defects | 0 blocking for S12-04 |
| Completed Tasks | **S12-04 (GET/PUT /mcp/tool-risk, per-server overrides, multiplex/dynamic/invoke hide)** |

---

**Test Cycle:** QA-013 (Sprint 12 / MCP OAuth Broker BL-067) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 12 S12-03 Test Results (BL-067 Vault-backed Token Broker)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (oauth + multiplex + catalog) | **22 passed**, 0 failed |
| Coverage | Token freshness/skew, client_credentials & refresh forms, grant apply, public status never leaks secrets, broker token overrides static auth_header |
| Open defects | 0 blocking for S12-03 |
| Completed Tasks | **S12-03 (mcp_oauth_credentials + vault paths, GET/PUT/POST refresh/DELETE, MCP Governance broker card)** |

---

**Test Cycle:** QA-012 (Sprint 12 / MCP Catalog BL-066) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 12 S12-02 Test Results (BL-066 Curated Catalog + Install)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (catalog + multiplex + dynamic tools) | **21 passed**, 0 failed |
| Coverage | Curated slugs, install spec + catalog_slug, already-installed detect, custom transport URL validation |
| Open defects | 0 blocking for S12-02 |
| Completed Tasks | **S12-02 (GET /mcp/catalog, POST /mcp/catalog/{slug}/install, POST /mcp/catalog/custom, MCP Governance catalog card)** |

---

**Test Cycle:** QA-011 (Sprint 12 / MCP Multiplex BL-065) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 12 S12-01 Test Results (BL-065 Single MCP Gateway URL)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (multiplex + related) | **18 passed**, 0 failed |
| Coverage | Server slug, qualified tool names, catalog prefixing, initialize/tools/list JSON-RPC, unique unqualified resolve |
| Open defects | 0 blocking for S12-01 |
| Completed Tasks | **S12-01 (POST /v1/mcp + /api/v1/mcp, MCP Governance URL card)** |

---

**Test Cycle:** QA-010 (Sprint 11 Exit / Compounding Cost S11-05 / M9) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 11 S11-05 Test Results (Compounding Cost Report)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (compounding + token saving + dynamic tools) | **22 passed**, 0 failed |
| Coverage | Stacked compression + tools USD, cheaper-model routing layer, narrative mentions all three layers |
| Open defects | 0 blocking for Sprint 11 |
| Milestone Status | **M9 — Cost & Prompt Parity APPROVED** |
| Completed Tasks | **S11-05 (Executive compounding cost section + catalog PDF report)** |

---

**Test Cycle:** QA-009 (Sprint 11 / Dynamic Tool Calling BL-064) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 11 S11-03 / S11-04 Test Results (BL-064 Rank, Cap, Preview)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (dynamic tools + token saving + UAG) | **27 passed**, 0 failed |
| Coverage | Cap at N, query-relevant ranking, ≥50% token KPI on large catalogs, catalog from schemas/names, request override, MCP settings + preview API |
| Open defects | 0 blocking for S11-03 / S11-04 |
| Completed Tasks | **S11-03, S11-04 (BL-064 Complete)** |

---

**Test Cycle:** QA-008 (Sprint 11 / Token Saving Dashboard S11-02) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 11 S11-02 Test Results (BL-063 Dashboard Before/After)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (token saving + summary) | **11 passed**, 0 failed |
| Coverage | Aggregate original/compressed tokens, ignore zero-savings rows, dashboard overview `token_saving` payload |
| Open defects | 0 blocking for S11-02 |
| Completed Tasks | **S11-02 (Token saving dashboard Complete)** |

---

**Test Cycle:** QA-007 (Sprint 11 / Token Saving BL-063 Validation) — **PASSED**  
**Completed:** Aug 13, 2026

### Sprint 11 S11-01 Test Results (BL-063 Token Saving Engine)

| Metric | Value |
|--------|-------|
| Pass rate | **100%** |
| pytest (token saving) | **8 passed**, 0 failed |
| Coverage | TOON encode, markdown strip, JSON fence compression, tenant/request config resolution, gateway ingress wiring |
| Open defects | 0 blocking for S11-01 |
| Completed Tasks | **S11-01 (BL-063 Backend Complete)** |

---

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
