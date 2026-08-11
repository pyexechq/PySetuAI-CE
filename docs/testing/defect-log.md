# PySetu AI — Defect Log

**Last Updated:** Aug 11, 2026  
**Test Cycle:** QA-001

---

## Open Defects

| ID | Severity | Module | Title | Description | Status | Found In |
|----|----------|--------|-------|-------------|--------|----------|
| DEF-001 | **S1** | MCP Governance | No policy enforcement on tool invoke | `POST /mcp/servers/{id}/tools/invoke` calls `invoke_mcp_tool()` directly without policy engine evaluation. Seeded "Tool Allowlist" and "Rate Limiting" policies are not enforced at runtime. Any user with `manage_mcp` permission can invoke any tool on any registered server. | Open | QA-001 |
| DEF-002 | **S2** | MCP Governance | No audit trail on MCP tool invoke | MCP tool invocations do not create audit log entries. Violates auditability requirement for MCP governance module. Gateway requests are audited; MCP admin invokes are not. | Open | QA-001 |
| DEF-003 | **S2** | Studio | MCP Simulator uses client-side mock | Studio MCP Simulator tab simulates tool responses in the browser instead of calling `POST /mcp/servers/{id}/tools/invoke`. Results do not match runtime behavior; QA cannot validate MCP governance through Studio. | Open | QA-001 |
| DEF-004 | **S2** | Security | Alert webhooks not wired to events | Alert webhook CRUD and manual test work, but no automatic dispatch occurs on policy violations, security detections, or audit events. Security Center alerts are display-only. | Open | QA-001 |
| DEF-005 | **S1** | Multi-Tenant | No integration tests for tenant isolation | Application-layer tenant scoping exists (`tenant_id` in queries, JWT mismatch check), but zero integration tests verify cross-tenant access is blocked. Cannot certify isolation without automated evidence. | Open | QA-001 |
| DEF-006 | **S2** | Security | OPA ABAC disabled and fail-open by default | `opa_enabled=False`, `opa_fail_open=True` in default config. ABAC overlay is implemented but not active. Production deployments may ship without ABAC unless explicitly configured. | Open | QA-001 |
| DEF-007 | **S3** | LLM Router | Gateway mock mode default | `gateway_mock_mode=True` means chat completions return simulated responses. Cannot validate real OpenAI/Gemini/Ollama routing without API keys and mock mode disabled. | Open | QA-001 |
| DEF-008 | **S3** | Compliance | Heuristic scoring only | Compliance framework scores are calculated from tenant configuration signals, not formal GRC attestation. Several controls hardcoded as `not_met`. UI may overstate compliance posture. | Open | QA-001 |
| DEF-009 | **S3** | Documentation | Testing README stale | `docs/testing/README.md` states "no automated tests yet" but 44 pytest tests exist and pass. Misleads QA and release reviewers. | Open | QA-001 |
| DEF-010 | **S3** | Documentation | API reference incomplete | `docs/api/README.md` documents 4 endpoints; ~120 are implemented. Release reviewers cannot validate API coverage from docs. | Open | QA-001 |
| DEF-011 | **S3** | Documentation | Security handoff stale | `docs/handoffs/security-agent.md` lists rate limiting and RBAC as missing; both are implemented (S6-04). | Open | QA-001 |
| DEF-012 | **S3** | Documentation | Known issues stale | KI-004 ("mock data") and KI-006 partial status not updated to reflect live API integration. | Open | QA-001 |
| DEF-013 | **S4** | Backend | Duplicate gateway router registration | `gateway_router` registered twice in `main.py` (lines 81–82). Harmless but indicates code hygiene gap. | Open | QA-001 |
| DEF-014 | **S3** | Frontend | No automated frontend tests | Zero Vitest, Testing Library, or Playwright tests. All frontend validation is manual or build-only. | Open | QA-001 |
| DEF-015 | **S3** | Settings | OIDC JIT toggle missing in UI | Backend supports `OIDC_JIT_PROVISION_DEFAULT` and per-tenant JIT gate; Settings → Identity has OIDC CRUD but no JIT toggle (S6-05). | Open | QA-001 |
| DEF-016 | **S2** | Security | No auth event audit logging | Login success/failure, OIDC callbacks, and session events are not written to audit log. Security architecture requires auth event auditing. | Open | QA-001 |
| DEF-017 | **S3** | MCP Governance | stdio transport skipped | MCP servers using stdio transport cannot be health-checked or discovered remotely. Documented as skipped; limits MCP coverage for local agent setups. | Open | QA-001 |
| DEF-018 | **S3** | Audit | No immutable audit chain | Audit logs are mutable database records with no tamper-evident chain or WORM storage. Compliance frameworks requiring immutable audit trails are not met. | Open | QA-001 |

---

## Severity Summary

| Severity | Open | Fixed | Total |
|----------|------|-------|-------|
| S1 (Security / Data) | 2 | 0 | 2 |
| S2 (Core Feature) | 5 | 0 | 5 |
| S3 (Functional) | 10 | 0 | 10 |
| S4 (Cosmetic) | 1 | 0 | 1 |
| **Total** | **18** | **0** | **18** |

---

## Previously Known Issues (Cross-Reference)

| Known Issue | Defect | Notes |
|-------------|--------|-------|
| KI-005 JWT secret dev default | Partially mitigated | Vault integration (S6-01) + prod guard; rotation tracked as S6-06 |
| KI-006 RBAC client-side only | Mitigated in code | Backend RBAC module exists; integration tests still missing (DEF-005) |
| KI-004 Mock data modules | Resolved | Live API wired; doc not updated (DEF-012) |

---

## Defect Triage Recommendations

### Must fix before any production release (S1)

1. **DEF-001** — Add policy engine gate to MCP tool invoke
2. **DEF-005** — Add cross-tenant isolation integration tests

### Should fix before M5 (S2)

3. **DEF-002** — Audit MCP tool invocations
4. **DEF-003** — Wire Studio MCP Simulator to live API
5. **DEF-004** — Wire alert webhooks to gateway/audit events
6. **DEF-006** — Enable OPA fail-closed in production config template
7. **DEF-016** — Audit auth events (login, failed attempts, OIDC)

### Track for sprint backlog (S3/S4)

- Remaining documentation updates (DEF-009 through DEF-012)
- Frontend test suite (DEF-014)
- OIDC JIT toggle (DEF-015, tracked as S6-05)
- Gateway mock mode documentation (DEF-007)
- Compliance scoring disclaimer (DEF-008)
