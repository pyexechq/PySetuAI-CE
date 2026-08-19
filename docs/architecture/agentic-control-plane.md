# Unified AI Agent Control Plane — Architecture

**Status:** Phase 1 foundation in progress
**Related:** [agentic-control-plane-roadmap.md](../planning/agentic-control-plane-roadmap.md)

## 1. Problem

PySetu governs AI API traffic at the gateway. The control-plane vision extends governance to
**where AI action originates**: local coding agents, IDE copilots, MCP clients, Microsoft
Copilot/Teams agents, and enterprise AI apps.

```
                    PySetu AI
                AI Control Plane
                       |
       +---------------+----------------+
       |               |                |
       v               v                v
   Endpoint        Enterprise       AI Gateway
   Governance      Agent Governance  Governance
       |               |                |
       +---------------+----------------+
                       |
              Unified Policy Engine
                       |
              Unified DLP + Risk Engine
                       |
              Unified Audit + Analytics
```

## 2. What already exists (reused, not rebuilt)

| Capability | Reused file |
|-----------|-------------|
| Tenant JWT auth + RBAC | `backend/app/core/security.py`, `backend/app/core/rbac.py`, `backend/app/core/deps.py` |
| Client API-key auth (non-interactive callers) | `get_current_client()` in `backend/app/core/deps.py` |
| Policy evaluation | `backend/app/services/policy_engine.py` |
| DLP classification + redaction | `backend/app/services/dlp_service.py` |
| Audit log + bodies | `AuditLog`, `AuditLogBody` in `backend/app/models/governance.py` |
| Incident dispatch + SIEM | `backend/app/services/incident_dispatch_service.py`, `siem_connector_service.py` |
| MCP inventory + tool risk | `MCPServer`, `backend/app/services/mcp_tool_risk_service.py` |
| Frontend design system | `frontend/src/components/ui/*`, `frontend/src/config/navigation.ts` |

`MCPServer` and `LLMProvider` remain specialized registries. The new `AgentInventory` model links
to them and to endpoints instead of replacing them.

## 3. Phase 1 data model

```
Endpoint 1──* AgentInventory 1──* AgentCapability
   │              │
   │              └────────────────┐
   │                               │
   └────────────────────────── SecurityEvent ──> AuditLog
```

- **Endpoint** — registered device/host. Unique per `(tenant_id, hostname)`.
- **AgentInventory** — discovered or registered AI agent (coding agent, IDE copilot, MCP agent, …).
- **AgentCapability** — what an agent can do (`file.read`, `shell.exec`, `mcp.tool`, …).
- **SecurityEvent** — normalized event with a `decision`, `risk_score`, and `classification`.
  Each event also writes an `AuditLog` row (`source="endpoint"`) so it appears in Audit Explorer.

## 4. Unified security event contract

```json
{
  "event_id": "<uuid>",
  "tenant_id": "<uuid>",
  "source": "endpoint",
  "user_name": "alice",
  "endpoint_id": "<uuid|null>",
  "agent_id": "<uuid|null>",
  "event_type": "file",
  "tool": "claude-code",
  "action": "file.read",
  "resource": ".env",
  "classification": ["SECRET"],
  "decision": "blocked",
  "risk_score": 90,
  "policy_id": "<uuid|null>",
  "metadata": {}
}
```

Raw file contents and secrets are **not** uploaded by default. Endpoints send paths, hashes,
classifications, and decisions; full content capture is opt-in and policy-gated.

## 5. Phase 1 API surface

```
POST /api/v1/endpoints                     register (client API key)
POST /api/v1/endpoints/{id}/heartbeat      heartbeat (client API key)
GET  /api/v1/endpoints                     list (JWT, VIEW_AGENTS)
POST /api/v1/agents                        upsert (client API key)
GET  /api/v1/agents                        list (JWT, VIEW_AGENTS)
GET  /api/v1/agents/{id}                   detail (JWT, VIEW_AGENTS)
POST /api/v1/security-events/ingest        ingest (client API key)
GET  /api/v1/security-events               list (JWT, VIEW_AUDIT_LOGS)
GET  /api/v1/security-events/summary       aggregate (JWT, VIEW_AUDIT_LOGS)
```

## 6. Enforcement boundaries (honest limits)

| Surface | Phase 1 behavior |
|---------|------------------|
| Browser extension | Existing protected sites only |
| MCP gateway | Existing multiplex governance |
| Endpoint daemon | Discovery + telemetry first |
| File/shell interception | Per-OS adapters later; no kernel hooks |
| Chrome native "Ask Gemini" | Not interceptable by MV3 extension |
| Microsoft-managed Copilot ops | Inventory/audit sync via Graph/Audit APIs, not universal real-time interception |

## 7. Security model

- Endpoint and agent identity never rely on display names alone.
- Endpoint registration and event ingestion use client API keys with origin allowlisting.
- Policies remain authoritative; decisions are logged even when cached offline.
- Audit rows are tenant-scoped, tamper-resistant, and searchable.

## 8. Endpoint daemon (Phase 1)

The reference daemon lives in `endpoint-agent/` as a standard-library-only Python
package. It registers the endpoint, heartbeats, discovers AI tools from binaries,
config directories, and VS Code extensions, and ingests discovery events.

```bash
python -m pysetu_agent --once   # single pass
python -m pysetu_agent          # loop
python -m pysetu_agent --scan-dir . --policy-file policy.json
```

## 9. Local DLP, policy, and scanning (Phase 2)

- `detection.py` — secrets (private keys, AWS/OpenAI/GitHub/Slack tokens, JWT,
  generic `key=value` assignments) and PII (SSN, email, phone, EU IDs, card
  numbers). Detection returns a redacted copy; raw content is never uploaded.
- `policy.py` — rule evaluation (`pattern` + `classification` → `action`) with
  precedence `block > approval > redact > log > allow`, plus a file-backed
  `PolicyCache` with a SHA-256 integrity checksum for offline decisions.
- `scan.py` — walks a directory tree, skips build/dependency folders, and emits
  `FileScanEvent`s for files with findings.

## 10. Approval workflow

- `ApprovalRequest` (migration `068`) is created automatically when an ingested
  security event has `decision="approval"`, with a 24-hour expiry.
- `GET /api/v1/approvals` lists pending requests; `POST /approvals/{id}/approve`
  and `/reject` decide them. Decisions are tenant-scoped and reject
  already-decided requests.

## 11. Policy sync and shell governance (Phase 2)

- `PolicyBundle.file_governance_rules` (migration `069`) holds path-pattern rules
  (`pattern` + `classification` → `action`). `GET /agentic/policy` returns the
  effective rules for a client key's bundle, falling back to builtin defaults.
- The endpoint daemon fetches this policy into its integrity-checked
  `PolicyCache` during `--scan-dir`, falling back to cached/defaults offline.
- `endpoint-agent/pysetu_agent/shell.py` classifies shell commands as
  allow / approval / block with an ordered heuristic rule list.
- `endpoint-agent/pysetu_agent/watcher.py` provides a portable polling file
  watcher (snapshot diff → scan changed files). Native FSEvents/inotify is a
  future per-OS enhancement.
- `python -m pysetu_agent --watch DIR` runs continuous file monitoring, and
  `endpoint-agent/deploy/` provides launchd (macOS) and systemd (Linux) service
  definitions for background operation.
- The Approval Center UI at `/approvals` lists pending requests and supports
  approve/reject actions backed by the `/approvals` API.

## 12. MCP governance depth (Phase 3)

- `MCPToolPolicy` (migration `070`) holds per-tool governance actions
  (`allow` / `approval` / `block`) keyed by `(tenant_id, server_id, tool_name)`.
  `mcp_tool_policy_service` resolves the effective action, defaulting to
  `allow` when no policy exists so existing behavior is unchanged.
- `MCPToolChainEvent` (migration `070`) records each governed MCP tool
  invocation: source/target agent, endpoint, MCP server, tool, data source,
  external service, decision, and a deterministic 0–100 chain risk score.
- `mcp_tool_chain_service` computes chain risk from tool risk class plus
  bounded contributions from sensitive data sources, unknown external
  services, agent risk, and MCP server risk. It also builds the agentic
  attack-surface graph (agent → agent → server → tool → data → external).
- The gateway `before_invoke` hook now composes the deny-list + bundle scope
  (hard `block` baseline) with the per-tool policy. An `approval` action
  creates a `pending` `ApprovalRequest` via the unified security-event
  pipeline and returns JSON-RPC error `-32005` with `approval_request_id`.
- Allowed invocations emit a `MCPToolChainEvent` via `log_mcp_chain_event`
  (best-effort, never blocks the hot path).
- API surface: `GET/PUT/DELETE /mcp/tool-policies`, `GET /mcp/tool-chains`,
  `GET /mcp/tool-chains/summary`, `GET /mcp/tool-chains/graph`.
- The MCP Tool Chains UI at `/mcp-tool-chains` shows summary cards, the
  attack-surface map (ReactFlow), and the recent chain-event feed with
  decision filtering.
