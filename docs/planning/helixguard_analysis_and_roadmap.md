# HelixGuard AI — Feature Analysis & PySetuAI Adoption Roadmap

> **Source:** `/Users/sandeepshrivastava/Downloads/helixguard_ai_dashboard.tsx`  
> **Purpose:** Deep review of HelixGuard's LLM Router and MCP Registry & Governance modules, mapped to PySetuAI's current state and future roadmap.

---

## 1. What HelixGuard Does — Feature Analysis

HelixGuard is an "AI Control Plane" with 6 core views. This review focuses on the two you highlighted.

---

### 🔀 LLM Router (Lines 1524–1990)

This is the most sophisticated module in the file. It solves **intelligent, policy-driven request routing** across a heterogeneous model fleet.

#### Key Concepts

| Concept | HelixGuard Implementation |
|---------|--------------------------|
| **Routing Rules** | Named, ordered rules with CEL (Common Expression Language) condition logic, e.g. `data.classification IN ['Secret', 'Restricted']` |
| **Model Registry** | Registered models with provider, deployment type (Cloud vs. Local Air-gapped), context window, and per-1M-token cost |
| **Rule → Model Mapping** | Each rule explicitly maps to 1..N target models/pools; multi-model rules enable load-balancing |
| **Visual Routing Engine** | Dynamic SVG diagram showing request → Routing Engine → fan-out paths to target models, with traffic % per model |
| **Response Format Translation** | Each rule defines a `responseFormat` (OpenAI Compatible, Anthropic Native, Vertex Native, Universal Auto-Negotiated) — the gateway translates the upstream provider response before returning to the client |
| **API Key ↔ Rule Assignment** | Virtual API keys (prefixed `hx-prod-`, `hx-fin-`) are associated to specific routing rules — a client's key determines which routing rule fires |
| **Performance Tab** | Real latency charts per model — notably shows local air-gapped models have *lower* latency due to zero network overhead |
| **Cost Management Tab** | Cumulative spend vs. budget; surfaces $4,250 saved/month via smart routing — decomposes into "Routed to Local Models" and "Prompt Redaction Caching" |

#### Routing Rule Shape
```typescript
{
  id: number,
  title: string,          // "High Security / Restricted Data"
  desc: string,
  condition: string,      // CEL expression: "data.classification IN ['Secret', 'Restricted']"
  targetModels: string[], // ["Llama 3 70B"] or ["GPT-4o", "Claude 3.5", "Gemini 1.5 Pro"]
  responseFormat: string, // "OpenAI Compatible (REST)" | "Universal (Auto-Negotiated)" | ...
  active: boolean
}
```

#### What Makes It Excellent
1. **CEL conditions** — human-readable, auditable, extensible condition language rather than code
2. **Visual fan-out diagram** — immediately shows how a rule distributes traffic (percentages, air-gapped vs cloud badge)
3. **Response format normalization** — the universal gateway abstraction means clients never need to change; HelixGuard normalizes the upstream response
4. **API Key ↔ Rule binding** — very elegant; each service/key has its own routing profile without needing to pass routing context in headers

#### What PySetuAI Already Has
- ✅ LLM Router backend with dynamic rule CRUD (BL-050, Phase 6 — done)
- ✅ Routing groups — group-as-model, weighted pools, auto-failover (BL-060, Phase 7 — done)
- ✅ Regional routing groups (BL-077, Phase 7 — done)
- ✅ LLM Router UI with routing donut + rules (Phase 2 — done)
- ✅ Cost management / compounding savings report (BL-063, BL-064 — done)

#### Gap Analysis vs. HelixGuard LLM Router

| HelixGuard Feature | PySetuAI Today | Gap |
|-------------------|---------------|-----|
| CEL expression conditions | Uses rule conditions but unclear if CEL | **Validate/upgrade to CEL syntax** |
| Visual SVG fan-out routing diagram | "Routing donut" exists but different | **Enhanced visual routing engine** |
| Response format translation per rule | Universal Gateway handles this | **Expose per-rule format config in UI** |
| API Key ↔ Routing Rule assignment | Keys exist, binding unclear | **Explicit key→rule binding UI** |
| Performance latency chart per model | Partial in Observability | **Model-level latency tab in Router** |
| Cost savings decomposition (local vs cloud) | Compounding cost report exists | **Decompose savings by routing strategy** |
| Rule simulation (Simulate button) | Studio/Sandbox exists | **Wire "Simulate" to routing rules** |

---

### 🏛️ MCP Registry & Governance (Lines 397–702)

This module governs all MCP server connections at an enterprise level — registration, trust scoring, RBAC, and alerting.

#### Key Concepts

| Concept | HelixGuard Implementation |
|---------|--------------------------|
| **MCP Server Registration Wizard** | 3-step modal: (1) Protocol selection (SSE / Streamable HTTP / REST→MCP), (2) Connection test / schema parse, (3) RBAC assignment |
| **3 Connection Protocols** | SSE, Streamable HTTP, **Dynamic REST-to-MCP** (auto-generate MCP proxy from OpenAPI/Postman/GraphQL schema) |
| **Trust Score** | Per-server numeric score 0–100; visualized with a colored progress bar; drives risk classification (Low/Medium/High) |
| **Trust Score Distribution** | Donut chart showing fleet-wide trust posture (Low/Medium/High %) |
| **Tool-level Inventory** | Every tool has: parent server, risk profile, daily call count, avg latency, status (Active/Blocked) |
| **RBAC Access Control** | Groups (Finance Analysts, HR Managers, etc.) → Allowed Servers + Denied Tools lists |
| **Recent Alerts** | Feed showing high-risk tool calls, unusual access patterns, server blocks |
| **API→MCP Wizard** | The standout feature: upload OpenAPI spec → auto-map REST endpoints to MCP tools → set RBAC in one wizard |

#### REST-to-MCP Auto-Generation (The Killer Feature)
```
Step 1: Select protocol = "Dynamic (REST to MCP)"
        Choose source: OpenAPI/Swagger | Postman Collection | GraphQL Schema
        Upload JSON/YAML/TXT file (up to 10MB)
Step 2: "Parse Schema" → shows mapped REST endpoints as MCP tools
Step 3: Set Permitted LLMs + Permitted User Roles (RBAC)
→ "Publish MCP Server"
```
This means **any existing REST API can become an MCP server** without touching its code — HelixGuard acts as a transparent proxy.

#### Authentication Context Injection (Security Innovation)
> *"HelixGuard will automatically inject the authenticated user's Bearer token into downstream REST API calls based on their Active Directory / SSO context. The LLM will never see the actual API keys."*

This is a critical enterprise security control — the LLM context never contains real credentials.

#### What PySetuAI Already Has
- ✅ MCP Governance UI — inventory + KPIs (Phase 2 — done)
- ✅ MCP catalog — curated library + one-click install + custom transport URL (BL-066, Phase 9 — done)
- ✅ MCP multiplex — single gateway URL (BL-065, Phase 9 — done)
- ✅ OAuth auth mediation for MCP credentials (BL-067, Phase 9 — done)
- ✅ Tool risk taxonomy — read/write/destructive + auto-hide (BL-068, Phase 9 — done)
- ✅ MCP live trust/risk scoring backend (BL-051, Phase 6 — done)

#### Gap Analysis vs. HelixGuard MCP Governance

| HelixGuard Feature | PySetuAI Today | Gap |
|-------------------|---------------|-----|
| **REST-to-MCP wizard** (OpenAPI → auto-proxy) | Not present | **New Feature: BL-083** |
| **GraphQL Schema → MCP** | Not present | **New Feature: BL-083** |
| **Postman Collection → MCP** | Not present | **New Feature: BL-083** |
| **3-step registration wizard UI** | Custom transport URL only | **Upgrade: registration wizard flow** |
| **Credential/token injection** (SSO context, LLM never sees keys) | OAuth mediation exists | **Strengthen: SSO context forwarding** |
| **Per-tool call counts + latency in UI** | Tool risk exists, usage partial | **BL-072 will cover this partially** |
| **Trust score donut fleet view** | Trust/risk scoring backend exists | **Wire score to fleet donut chart** |
| **RBAC: Allowed Servers + Denied Tools per group** | Role-based MCP access exists | **Granular tool-level deny lists in UI** |
| **MCP Alert feed** | Alerts exist | **MCP-specific alert feed in governance UI** |
| **Streamable HTTP protocol** | SSE + HTTP stream support unclear | **Validate and expose in wizard** |

---

## 2. PySetuAI Current State vs. HelixGuard

```mermaid
quadrantChart
    title PySetuAI vs HelixGuard Feature Coverage
    x-axis Low Coverage --> High Coverage
    y-axis Low Priority --> High Priority
    quadrant-1 "Invest Now"
    quadrant-2 "Maintain"
    quadrant-3 "Low Priority"
    quadrant-4 "Already Winning"

    REST-to-MCP Wizard: [0.05, 0.95]
    CEL Condition Syntax: [0.35, 0.75]
    Credential Injection (SSO→MCP): [0.45, 0.90]
    Visual Routing Fan-out: [0.40, 0.65]
    Tool-level RBAC Deny Lists: [0.50, 0.80]
    Per-rule Response Format UI: [0.55, 0.60]
    API Key→Rule Binding: [0.60, 0.70]
    Model Perf Chart in Router: [0.65, 0.55]
    Trust Score Fleet Donut: [0.70, 0.50]
    MCP Alert Feed: [0.75, 0.60]
    Dynamic Tool Calling: [0.90, 0.85]
    Auth Mediation (OAuth): [0.85, 0.90]
    Routing Groups+Failover: [0.90, 0.80]
    MCP Catalog: [0.88, 0.75]
```

---

## 3. Adoption Roadmap — New Backlog Items

These are **net-new items** derived from HelixGuard analysis, not yet covered by existing BL-0xx items.

### Tier 1 — High Impact (Add to Phase 9/10)

#### BL-083 — REST-to-MCP Auto-Proxy Wizard
**Inspired by:** HelixGuard `ApiToMcpWizard` component (Lines 131–395)  
**What:** 3-step UI wizard to register a new MCP server via:
- Native SSE or Streamable HTTP connection (test + discover tools)
- Dynamic REST→MCP: upload OpenAPI spec / Postman collection / GraphQL schema → auto-generate MCP tool proxy

**Backend:** Parse OpenAPI YAML/JSON → generate tool definitions → create virtual MCP server record → proxy requests through gateway  
**Value:** Transforms PySetuAI from "connect MCP servers" to "make any REST API an MCP server"  
**Effort:** L (3–4 sprints)  
**Priority:** P1

#### BL-084 — SSO Context Credential Injection
**Inspired by:** HelixGuard `ApiToMcpWizard` Step 3 — Authentication Context section  
**What:** When an authenticated user invokes an MCP tool backed by a REST API, PySetuAI injects the user's SSO Bearer token (from their OIDC session) into the downstream API call. The LLM prompt never contains actual API credentials.  
**Backend:** Token broker enhancement — forward OIDC `access_token` to specific MCP server endpoints based on server config  
**Value:** Critical enterprise security control — prevents credential leakage via LLM context  
**Effort:** M (1–2 sprints)  
**Priority:** P1

#### BL-085 — Tool-Level RBAC Deny Lists
**Inspired by:** HelixGuard MCP Access Policies tab — "Explicitly Denied Tools" per RBAC group  
**What:** In MCP governance, allow groups to have both:
- ✅ Allowed Servers (existing)
- ❌ Explicitly Denied Tools (net-new) — e.g. `delete_invoice`, `process_refund` blocked for Finance Analyst group even on an allowed server  
**Effort:** S (1 sprint)  
**Priority:** P1

### Tier 2 — Medium Impact (Phase 10/11)

#### BL-086 — Enhanced Visual Routing Engine
**Inspired by:** HelixGuard `LLMRouterView` — dynamic SVG fan-out diagram (Lines 1641–1706)  
**What:** Upgrade the existing LLM Router UI routing diagram to show:
- Fan-out SVG paths from Routing Engine to each target model
- Traffic % per model (for multi-model load-balancing rules)
- Cloud vs. Air-Gapped badges
- Animated SVG paths (pulsing for single model, dashed for multi)
- Rule simulation mode (click rule → see diagram update instantly)  
**Effort:** M (1 sprint — frontend only)  
**Priority:** P2

#### BL-087 — Per-Rule Response Format Configuration
**Inspired by:** HelixGuard `RuleModal` — "Client Response Format (Translation)" field  
**What:** Expose response format normalization per routing rule in the UI:
- OpenAI Compatible (REST) — default
- Anthropic Native
- Google Vertex Native
- Universal (Auto-Negotiated)  
**Note:** Backend Universal Gateway already handles protocol translation (M7 complete). This surfaces the per-rule config in the rule editor.  
**Effort:** S (< 1 sprint)  
**Priority:** P2

#### BL-088 — API Key ↔ Routing Rule Explicit Binding
**Inspired by:** HelixGuard `LLMRouterView` Rule Details panel — "Assigned API Keys / Clients" section  
**What:** In the Rule Details panel, show which API keys/service accounts are bound to this routing rule. Allow assigning/removing keys from within the rule view.  
**Effort:** S (1 sprint)  
**Priority:** P2

#### BL-089 — MCP Governance Alert Feed
**Inspired by:** HelixGuard MCP Overview tab — "Recent Alerts" section  
**What:** Dedicated alert feed in MCP Governance showing:
- High-risk tool calls (e.g., `delete_user` called)
- Unusual data access patterns per server
- Server blocks due to policy violation  
**Note:** Alerts infrastructure (BL-075) already wired. This surfaces MCP-specific alerts within the governance module.  
**Effort:** S (< 1 sprint)  
**Priority:** P2

#### BL-090 — Trust Score Fleet Donut Chart
**Inspired by:** HelixGuard MCP Overview — "Trust Score Distribution" donut chart  
**What:** Fleet-level donut chart in MCP Governance Overview showing distribution of servers by trust score band (Low 0–40 / Medium 41–70 / High 71–100).  
**Effort:** XS (< 0.5 sprint)  
**Priority:** P3

#### BL-091 — Model Performance Tab in LLM Router
**Inspired by:** HelixGuard `LLMRouterView` Performance tab — latency + throughput charts per model  
**What:** Add a Performance tab in the LLM Router UI showing:
- Avg request latency per model (Line chart over time)
- Token throughput per model (Stacked bar chart)
- Call latency: local air-gapped vs cloud comparison  
**Note:** Observability data already flows via OTel (S3-05). This is a focused model-level view within the router context.  
**Effort:** S (1 sprint)  
**Priority:** P2

---

## 4. Updated Roadmap Integration

### Where These Items Fit

| Phase | Sprint | New Items |
|-------|--------|-----------|
| **Phase 9** | Sprint 12 (current) | — (S12-05–07 already planned) |
| **Phase 9** | Sprint 13 | BL-085 (Tool RBAC deny lists), BL-089 (MCP alert feed), BL-090 (trust donut) |
| **Phase 10** | Sprint 14 | BL-084 (SSO credential injection), BL-087 (per-rule format), BL-088 (key→rule binding) |
| **Phase 10** | Sprint 14 | BL-086 (visual routing engine), BL-091 (model perf tab) |
| **Phase 11** *(new)* | Sprint 15–16 | **BL-083 (REST-to-MCP wizard)** — this is the strategic differentiator |

---

## 5. Strategic Assessment

### What HelixGuard Does Better Today
1. **REST-to-MCP Wizard** — turns any REST API into an MCP server with zero backend changes. This is a **major differentiation gap** for PySetuAI.
2. **Visual routing clarity** — the fan-out SVG diagram is immediately intuitive for enterprise admins.
3. **Tool-level granular RBAC** — explicit deny lists per tool, not just per server.

### What PySetuAI Does Better Already
1. **Dynamic tool calling** — auto-ranking/filtering MCP tools per request (BL-064) is ahead of HelixGuard.
2. **Routing groups with auto-failover** — weighted pools and auto-failover (BL-060) are more sophisticated.
3. **Token saving engine** — JSON→TOON compression (BL-063) is a unique differentiation.
4. **Auth mediation** — OAuth credential broker for MCP (BL-067) is more production-hardened.
5. **OTel trace replay** — BL-074 done (S13-03): stage-by-stage replay from audit + OTel trace id in Monitoring and Audit Explorer.

### Key Takeaway
> PySetuAI is **ahead on backend engineering** (dynamic tools, compression, failover, OTel) and needs to **close the UI/UX gap** on two specific features: the REST-to-MCP wizard (BL-083) and the visual routing engine (BL-086). These are the features that would most impress enterprise buyers evaluating both products side-by-side.

---

## 6. Recommended Next Steps

1. **Immediate (Sprint 13):** Add BL-085, BL-089, BL-090 — all small, high-value UI enhancements
2. **Sprint 14:** BL-084 (SSO injection) + BL-086 (visual router) + BL-087, BL-088
3. **Sprint 15–16:** BL-083 (REST-to-MCP wizard) — the strategic flagship feature
4. **Update `product-roadmap.md`** and `backlog.md` with BL-083–BL-091
5. **Update `gateway-parity-roadmap.md`** — add REST-to-MCP auto-proxy as a new section

---

*Generated: Aug 13, 2026 — Based on HelixGuard AI Dashboard TSX (2094 lines) analysis against PySetuAI Phase 1–10 roadmap.*
