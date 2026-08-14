# MCP Policy Pipeline — Design Spec

**Status:** Approved (Aug 14, 2026)  
**Milestone:** M14 — MCP Compliance Pipeline  
**Sprint:** 18 (Layer 1), 19–20 (Layer 2–3)  
**Related:** [gateway-parity-roadmap.md](./gateway-parity-roadmap.md) · [mcp-policy-pipeline-plan.md](./mcp-policy-pipeline-plan.md)

---

## Problem

Today Client API Keys and the MCP tool registry are only connected **indirectly** via `tenant_id`. Keys carry an optional policy bundle for LLM inspect/DLP, but MCP `tools/list` and `tools/call` load **all tenant servers** without bundle allowlists, without `mcp_tool_deny_rules` enforcement on the gateway path, and without `AuditLog` rows on multiplex `tools/call`.

The compliance pipeline diagram (Policy → Router → Audit with framework checks) is the correct **north star**, but it cannot be marketed as current behavior until MCP invoke is gated, logged, and scoped.

---

## Goals

1. **Workload identity:** Client API Key → tenant + policy bundle (+ limits). JWT users → tenant + default bundle + role.
2. **Single enforcement surface:** One filter applied at chat tool injection and `/v1/mcp` multiplex.
3. **Truthful audit:** Every MCP tool invocation produces a searchable audit row with compliance metadata.
4. **Incremental compliance:** Layer framework-specific rules (GDPR/HIPAA/ISO/SOC2) on top of working gates, not as a monolithic pre-router engine.

---

## Non-goals (this milestone)

- Billing/invoicing for MCP calls
- Immutable WORM ledger (Layer 3 optional)
- SAML / SCIM
- Per-key MCP assignment table (bundle scope is sufficient for v1)

---

## Architecture (merged model)

```
Client API Key (hg_…) or JWT
    ↓
GatewayContext
  tenant_id, client_api_key_id?, user?, policy_bundle_id?, policy_bundle_name?
    ↓
Compliance gate (shared `filter_mcp_access`)
  ├─ tenant MCP catalog (mcp_servers)
  ├─ bundle MCP allowlist (empty = all tenant servers — compat default)
  ├─ agent toggles + destructive auto-hide + URL filters (existing)
  ├─ mcp_tool_deny_rules (role or synthetic `client_key` for hg_ keys)
  ├─ inspect_for_gateway on tool args (ingress) — uses bundle policies/intents
  └─ OPA ABAC (optional, existing fail-open path)
    ↓
Branch A: LLM chat — select_model (honor routing_rule_client_keys) + dynamic tools
Branch B: MCP multiplex — tools/list, tools/call
    ↓
Post-call: egress inspect on tool response (Layer 1 minimal; Layer 2 full redaction)
    ↓
AuditLog + usage_metadata.compliance_metadata
```

**Registry** = tenant inventory (`mcp_servers`). **Bundle** = what a workload may use. **Key** = who is calling.

---

## Data model

### Policy bundle MCP scope (Layer 1)

Add JSON on `policy_bundles` (no new table for v1):

```json
{
  "mcp_scope": {
    "mode": "all" | "allowlist",
    "entries": [
      { "server_id": "uuid", "tool_names": ["read_invoice"] }
    ]
  }
}
```

| `mode` | Behavior |
|--------|----------|
| `all` or missing | All tenant MCP servers (backward compatible) |
| `allowlist` | Only listed servers; `tool_names` empty = all tools on that server |

Migration: `053_policy_bundle_mcp_scope` — add nullable JSONB column `mcp_scope` default null (interpret as `all`).

### Audit compliance metadata

Extend `usage_metadata` on `AuditLog` (and gateway trace) with:

```json
{
  "compliance_metadata": {
    "auth_type": "client_key" | "jwt",
    "client_api_key_id": "uuid?",
    "policy_bundle_id": "uuid?",
    "policy_bundle_name": "string?",
    "mcp_server_id": "uuid?",
    "tool_name": "string?",
    "purpose": "string?",
    "lawful_basis": "string?",
    "deny_reason": "string?",
    "inspect_actions": ["redact", "block"]
  }
}
```

`purpose` / `lawful_basis` populated in Layer 2 from JWT claims or request metadata.

---

## Enforcement rules

### Deny lists (BL-085 completion)

- Load `mcp_tool_deny_rules` for tenant once per request.
- **JWT:** match `user.role` (existing BL-085 intent).
- **Client key:** match synthetic role `client_key` (configurable deny rules for machine identity).
- Apply on `tools/list` (hide) and `tools/call` (reject with 403 JSON-RPC error).

### Inspect (DLP / intents)

- **Ingress:** Before `tools/call`, run `inspect_for_gateway` on serialized tool name + arguments using key/bundle policies.
- **Egress:** After successful call, inspect tool result text before returning to client (Layer 1: block/redact via existing policy engine; Layer 2: dedicated MCP response redaction).

### Routing rule ↔ key binding (BL-088 completion)

- `select_model` must filter routing rules: if rule has assigned keys, only those keys may match; unassigned rules remain global.

---

## API / UI

| Surface | Change |
|---------|--------|
| Policy bundle CRUD | `mcp_scope` in request/response schema |
| Policy Studio / bundle editor | MCP allowlist picker (servers + optional tools) |
| Governance Graph | Show bundle MCP scope count next to key nodes |
| Audit Explorer | Filter/display `compliance_metadata` fields |

---

## Layer roadmap

| Layer | Backlog | Exit criteria |
|-------|---------|---------------|
| **1** | BL-098–BL-103 | MCP calls audited; deny + bundle scope + inspect on live path; routing keys honored |
| **2** | BL-104–BL-105 | Purpose/lawful_basis on JWT; full tool response redaction |
| **3** | BL-106–BL-108 | Framework rule packs; retention/erasure; optional WORM ledger |

---

## Testing

| ID | Case |
|----|------|
| MCP-005 | Tool permissions enforced on gateway multiplex |
| MCP-009 | Audit entry on every tools/call |
| MT-003 | Key in tenant A cannot invoke tenant B MCP (existing tenant isolation) |
| New | Key with allowlist bundle cannot call unlisted server |
| New | Deny rule blocks tools/call even if tool not in tools/list |
| New | Routing rule with assigned key does not apply to other keys |

---

## Compatibility

- Existing tenants: bundles without `mcp_scope` behave as **all tenant MCP** (no behavior change).
- New bundles created after UI ships: default UI to `allowlist` with empty entries = **no MCP** until admin assigns (safer default for new workloads).

---

## Open questions (deferred)

1. Should `client_key` deny rules be seeded by default for destructive tools?
2. Framework rule packs: OPA rego per pack vs. Python rule engine — decide in Layer 3 spike.
