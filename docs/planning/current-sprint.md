# Current Sprint — Sprint 21 (Phase 3, MCP Governance Depth)

**Updated:** Aug 19, 2026  
**Active focus:** Unified AI Agent Control Plane Phase 3 — per-tool MCP governance, tool-chain risk scoring, agentic attack-surface graph, and approval-center integration.

> Architecture: [agentic-control-plane.md](../architecture/agentic-control-plane.md)  
> Roadmap: [agentic-control-plane-roadmap.md](./agentic-control-plane-roadmap.md)

## Sprint 21 — MCP Governance Depth

| ID | Task | Status |
|----|------|--------|
| S21-01 | `MCPToolPolicy` + `MCPToolChainEvent` models + migration `070` | Done |
| S21-02 | `mcp_tool_policy_service` — per-tool allow/approval/block | Done |
| S21-03 | `mcp_tool_chain_service` — chain risk scoring, events, summary, graph | Done |
| S21-04 | `mcp_governance` API router (policies, chains, summary, graph) | Done |
| S21-05 | Gateway `before_invoke` approval-aware check + `_create_mcp_approval` | Done |
| S21-06 | Chain-event emission on allowed invocations (`log_mcp_chain_event`) | Done |
| S21-07 | MCP Tool Chains UI (`/mcp-tool-chains`) + nav + api client | Done |
| S21-08 | Unit tests (`test_mcp_governance.py`) | Done |
| S21-09 | MCP discovery from endpoint configs (`.mcp.json`, `.cursor/mcp.json`, Claude Desktop) | Done |
| S21-10 | Agent-to-agent attribution (source agent resolved from gateway actor) | Done |

## Exit criteria

- Per-tool policy action resolves to allow / approval / block; deny-list + bundle scope remain the hard block baseline.
- `approval` action creates a `pending` `ApprovalRequest` and returns `-32005` with `approval_request_id` to the caller.
- Every governed MCP `tools/call` records a `MCPToolChainEvent` with a deterministic 0–100 chain risk score.
- Attack-surface graph renders agent → agent → server → tool → data → external chains.
- MCP Tool Chains page renders from live APIs.

## Prior sprint (closed)

Sprint 20 (S20-01–S20-10) — Endpoint Enforcement.

## Sprint 20 — Endpoint Enforcement

| ID | Task | Status |
|----|------|--------|
| S20-01 | Local secret + PII detection (`endpoint-agent/pysetu_agent/detection.py`) | Done |
| S20-02 | Local policy engine + integrity-checked cache (`policy.py`) | Done |
| S20-03 | Directory scanner + daemon `--scan-dir` (`scan.py`, `daemon.py`) | Done |
| S20-04 | Approval workflow — model, migration `068`, `/approvals` API | Done |
| S20-05 | Endpoint agent unit tests (24 tests) | Done |
| S20-06 | File governance adapter (polling watcher) | Done |
| S20-07 | Shell command governance (heuristic pre-filter) | Done |
| S20-08 | Policy sync endpoint (control plane → agent) | Done |
| S20-09 | Approval Center UI | Done |
| S20-10 | `--watch` mode + background service (launchd/systemd) | Done |

## Exit criteria

- Secret/PII detection returns classifications and a redacted copy without uploading raw content.
- Local policy decisions are deterministic, with block > approval > redact > log > allow precedence.
- The policy cache detects tampering via a SHA-256 checksum.
- `decision="approval"` events create a `pending` `ApprovalRequest` with a 24h expiry.
- Approve/reject endpoints are tenant-scoped and reject already-decided requests.

## Prior sprint (closed)

Sprint 19 (S19-01–S19-08) — Agent Control Plane Foundation.

## Sprint 19 — Agent Control Plane Foundation

| ID | Task | Status |
|----|------|--------|
| S19-01 | `Endpoint` / `AgentInventory` / `AgentCapability` / `SecurityEvent` models + migration `067` | Done |
| S19-02 | Endpoint register/heartbeat/list APIs | Done |
| S19-03 | Agent inventory + capability APIs | Done |
| S19-04 | Unified security-event ingest + Audit Explorer linkage | Done |
| S19-05 | Deterministic risk scoring service | Done |
| S19-06 | Agent Inventory + Endpoint Security pages and nav | Done |
| S19-07 | Tests for risk scoring, schemas, and event normalization | Done |
| S19-08 | Endpoint daemon (discovery + telemetry skeleton) | Done |

## Exit criteria

- Endpoint registration is idempotent per `(tenant_id, hostname)` and authenticated via client API key.
- Every endpoint security event writes a `SecurityEvent` row and a linked `AuditLog` with `source="endpoint"`.
- Agent risk score is deterministic and bounded 0–100.
- Agent Inventory and Endpoint Security pages render from live APIs.

## Sprint 18 (closed)

Sprint 18 (BL-098–BL-103) — MCP compliance pipeline Layer 1.

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
| S18-07 | Tests + test-plan / release-readiness updates | Done (mcp_access + multiplex tests; RAG DLP suite) |

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
- **Aug 15 UX batch (BL-116–BL-122)** — documented in [aug-15-compliance-ux-update.md](../progress/aug-15-compliance-ux-update.md); run migrations `059` + `060` after pull
