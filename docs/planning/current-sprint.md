# Current Sprint — Sprint 25 (5-Pillar Agentic AI Governance & Sequence Defense)

**Updated:** Aug 29, 2026  
**Active focus:** Deterministic Zero-AI Inline Pre-Flight Interception, Sequential MCP Tool Chain State Machine, MITRE ATLAS/OWASP GenAI Compliance, Dynamic Cost Arbitrage Engine, and Distributed Edge Mesh.

> Architecture: [agentic-control-plane.md](../architecture/agentic-control-plane.md) · [security-architecture.md](../architecture/security-architecture.md)  
> Roadmap: [product-roadmap.md](./product-roadmap.md)

## Sprint 25 — 5-Pillar Agentic AI Governance & Sequence Defense

| ID | Task | Status |
|----|------|--------|
| S25-01 | Inline Zero-AI Pre-Flight Interceptor in `gateway_service.py` (< 0.3 ms scan latency, 100% attack recall, zero-token cost bypass) | Done |
| S25-02 | Security Provenance Headers (`X-PySetu-Action`, `X-PySetu-Risk`, `X-PySetu-Classifier-Verdict`) in `gateway.py` | Done |
| S25-03 | Audit Explorer Pre-Flight Classifier Telemetry Card & Rule Chips in `request-log-panel.tsx` | Done |
| S25-04 | Deterministic Sequential MCP Tool Chain State Machine in `mcp_sequence_detector.py` (Exfiltration, RCE, Destructive Mutations, Privilege Escalation, Runaway Loops) | Done |
| S25-05 | Server-Side Agentic Loop Enforcement in `_execute_upstream` in `gateway_service.py` | Done |
| S25-06 | MITRE ATLAS (6/6 Controls Met) & OWASP GenAI Top 10 (5/5 Controls Met) framework evaluators in `compliance_service.py` | Done |
| S25-07 | Automated Nightly 10,000 Golden Dataset Regression Benchmark Cron on Celery Beat (`02:00 UTC`) | Done |
| S25-08 | Dynamic Cost Arbitrage & Complexity Engine (`cost_arbitrage_service.py`, `llm_router.py`) with 91.7%–94.0% token savings | Done |
| S25-09 | Shadow AI Discovery Fleet API (`GET /api/v1/shadow-ai/summary`) in `agentic.py` | Done |
| S25-10 | Distributed Edge Mesh Wasm/JSON compiled rule sync (`GET /api/v1/edge/bundle`) packaging 22 rules & 5 MCP chains | Done |

## Exit criteria

- Gateway intercepts prompt injections in $< 0.3$ ms without calling upstream LLMs.
- Multi-step tool call sequences (e.g. read secret $\rightarrow$ http post) are intercepted in real-time before execution.
- Compliance Center displays MITRE ATLAS and OWASP GenAI Top 10 with 100% compliant scores.
- Nightly benchmark regression suite automatically guards 99%+ accuracy and 100% threat recall.
- Low-complexity prompts are dynamically downgraded with full cost savings telemetry.
- Regional edge mesh nodes receive compiled sync bundles with sub-1ms synchronization.

## Prior sprints (closed)

Sprint 24 (S24-01–S24-15) — Endpoint MCP Gateway + Sandbox Policy Dry-Run.

## Sprint 24 — Endpoint MCP Gateway + Sandbox Policy Dry-Run

| ID | Task | Status |
|----|------|--------|
| S24-01 | MCP gateway (`endpoint-agent/pysetu_agent/mcp_gateway.py`) — JSON-RPC framing, `GatewayDecision`, `decide_tool_call`, `McpServerProcess`, `handle_tool_call`, `handle_message`, `run_gateway`, `gateway_config`, `write_gateway_config` | Done |
| S24-02 | `DiscoveredMcpServer.args` field + `_mcp_server_args()` so the gateway spawns `npx -y @server-github` correctly | Done |
| S24-03 | Daemon CLI flags `--mcp-gateway`, `--server`, `--mcp-gateway-config`; offline dispatch before `missing_fields` check | Done |
| S24-04 | MCP gateway tests (`test_mcp_gateway.py`, 15 tests) + daemon CLI wiring tests | Done |
| S24-05 | Policy dry-run against API key bundles — `POST /policies/test` accepts `api_key_id`/`bundle_id`, returns per-rule `rule_results` | Done |
| S24-06 | `GET /policies/rules` accepts `bundle_id`/`default_bundle` to return bundle rules | Done |
| S24-07 | Governance Sandbox API key selector + real-time evaluation (300 ms debounce) + active-rule highlighting (passed/block/redact/alert) + triggered-rule progress bar | Done |
| S24-08 | Policy engine honors regex flags in `content.matches(/.../i)` | Done |
| S24-09 | Data Protection Center tabs (DLP scanner, movement policy, exemptions) | Done |
| S24-10 | Developer Portal (`/developer-portal`) — MCP Access Request submission + status UI | Done |
| S24-11 | API key auto-provisioning for approved MCP access requests | Done |
| S24-12 | Secure API Key and Claude Desktop `mcp.json` retrieval endpoint | Done |
| S24-13 | MCP Governance Access & RBAC table redesign — live Developer Portal grants table (`McpDeveloperGrantsCard`), granted operation chips, and revoke actions | Done |
| S24-14 | Consolidation of legacy Self-Service MCP Portal tab into unified Developer Portal (`/developer-portal`), per-server visibility controls, and `/mcp-portal` redirect | Done |
| S24-15 | SaaS Admin / Platform Operator Module Entitlement (`developer_portal` feature flag in `/platform`) and Tenant-Level portal disablement guard | Done |

## Exit criteria

- MCP gateway intercepts every `tools/call` from Claude Desktop / Cursor / VSCode and applies the local policy (secrets→block, PII→redact).
- Policy dry-run evaluates against the selected API key's attached bundle and highlights each active rule in real time.
- `content.matches(/pattern/flags)` conditions evaluate correctly (case-insensitive, multiline, dotall, verbose).
- External developers can submit MCP Access Requests via the Developer Portal, and retrieve auto-provisioned API keys upon approval.
- Tenant administrators can govern Developer Portal grants and individual MCP Server visibility (`Published`/`Hidden`).
- SaaS Platform Admins can license/entitle the Developer Portal per tenant from Platform Ops (`/platform`).

## Prior sprint (closed)

Sprint 23 (S23-01–S23-09) — Advanced Agentic Security.

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
| S18-06 | Bundle MCP scope UI in Policy Studio | Done |
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
