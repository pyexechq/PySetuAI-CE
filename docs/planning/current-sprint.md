# Current Sprint — Sprint 18 (Phase 13, Layer 1)

**Updated:** Aug 14, 2026  
**Active focus:** MCP compliance pipeline Layer 1 — audit, enforce deny lists, bundle MCP scope, DLP on tool path, routing key binding (BL-098–BL-103).

> Design: [mcp-policy-pipeline-design.md](./mcp-policy-pipeline-design.md)  
> Plan: [mcp-policy-pipeline-plan.md](./mcp-policy-pipeline-plan.md)

## Sprint 18 — MCP gateway enforcement

| ID | Task | Status |
|----|------|--------|
| S18-01 | Migration `053_policy_bundle_mcp_scope` + bundle API schemas | Done |
| S18-02 | `mcp_access_service` — bundle allowlist + deny rules | Done |
| S18-03 | Multiplex `tools/list` / `tools/call` gate + audit | Done |
| S18-04 | Chat path uses shared MCP access filter | Done |
| S18-05 | `select_model` honors `routing_rule_client_keys` | Done |
| S18-06 | Bundle MCP scope UI in Policy Studio | Pending |
| S18-07 | Tests + test-plan / release-readiness updates | Partial |

## Exit criteria

- Every multiplex `tools/call` writes `AuditLog` with `client_api_key_id` when applicable.
- `mcp_tool_deny_rules` enforced on live gateway (not admin API only).
- Policy bundle `mcp_scope` filters servers/tools; missing scope = all tenant MCP.
- Routing rules with assigned keys only match those keys.
- MCP-005, MCP-009, DEF-001 marked Pass in test plan.

## Previous sprint (closed)

Sprint 17 (BL-092–BL-097) complete Aug 14 — [quality-audit-sprint.md](./quality-audit-sprint.md).

## Optional / ops (not in sprint)

- BL-079 endpoint agent
- BL-038 git remote / push
- BL-039 full pytest CI
- BL-044 demo creds in prod
