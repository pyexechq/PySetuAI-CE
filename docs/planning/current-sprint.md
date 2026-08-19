# Current Sprint — Sprint 23 (Phase 5, Advanced Agentic Security)

**Updated:** Aug 19, 2026  
**Active focus:** Unified AI Agent Control Plane Phase 5 — anomaly detection, prompt-injection scanning, exfiltration detection, and the Guardian enforcement loop.

> Architecture: [agentic-control-plane.md](../architecture/agentic-control-plane.md)  
> Roadmap: [agentic-control-plane-roadmap.md](./agentic-control-plane-roadmap.md)

## Sprint 23 — Advanced Agentic Security

| ID | Task | Status |
|----|------|--------|
| S23-01 | `AgentAnomalyRecord` / `PromptInjectionFinding` / `ExfiltrationEvent` / `GuardianAction` models + migration `072` | Done |
| S23-02 | `anomaly_detection_service` — volume/tool/data/timing/chain-risk detectors | Done |
| S23-03 | `exfiltration_detection_service` — large/rapid/sensitive-boundary detectors | Done |
| S23-04 | `prompt_injection_scan_service` — wraps `scan_content`, persists findings | Done |
| S23-05 | `guardian_service` — severity→action evaluation + remediation execution | Done |
| S23-06 | `agentic_security` API router (anomalies, injection, exfil, guardian) | Done |
| S23-07 | Agentic Security UI (`/agentic-security`) + nav + api client | Done |
| S23-08 | Unit tests (`test_agentic_security.py`) | Done |
| S23-09 | Celery beat schedule for Guardian loop (`run_guardian_loop_all_tenants`) | Done |

## Exit criteria

- Anomaly/exfiltration detectors are pure, deterministic, and unit-testable.
- Prompt-injection scanning reuses `scan_content` and stores only a truncated preview.
- Guardian loop evaluates open findings and executes block/revoke/quarantine/alert remediation.
- Agentic Security page renders anomalies, findings, exfiltration, and guardian actions from live APIs.

## Prior sprint (closed)

Sprint 22 (S22-01–S22-07) — Microsoft Copilot.

## Sprint 22 — Microsoft Copilot

| ID | Task | Status |
|----|------|--------|
| S22-01 | `CopilotInstance` / `CopilotConnector` / `CopilotBaseline` / `CopilotDriftRecord` models + migration `071` | Done |
| S22-02 | `copilot_service` — connector/instance risk scoring | Done |
| S22-03 | Sync adapter — idempotent payload merge + soft-delete removal | Done |
| S22-04 | Drift detection — baseline capture + pure comparison + persistence | Done |
| S22-05 | `copilot` API router (instances, connectors, sync, drift, baselines, summary) | Done |
| S22-06 | Microsoft Copilot UI (`/microsoft-copilot`) + nav + api client | Done |
| S22-07 | Unit tests (`test_copilot_governance.py`) | Done |

## Exit criteria

- Connector and instance risk scores are deterministic 0–100 and reuse control-plane risk conventions.
- Sync is idempotent by `(tenant_id, external_id)`; removed entities are soft-deleted (`status="removed"`).
- Drift detection compares current state against a captured baseline and flags risk/status/new/removed changes.
- Microsoft Copilot page renders instances, connectors, and drift from live APIs.

## Prior sprint (closed)

Sprint 21 (S21-01–S21-10) — MCP Governance Depth.

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
