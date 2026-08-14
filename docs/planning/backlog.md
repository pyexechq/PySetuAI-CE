# Backlog

## P0 — Critical

| ID | Item | Module | Phase |
|----|------|--------|-------|
| BL-001 | Tenant-scoped JWT middleware | Backend | 1 |
| BL-002 | Alembic migrations for Tenant/User | Backend | 1 |
| BL-003 | Login page with auth flow | Frontend | 1 |
| BL-004 | RBAC route guards | Frontend | 1 |

## P1 — High

| ID | Item | Module | Phase |
|----|------|--------|-------|
| BL-012 | MCP server registration API | MCP Governance | 2 |
| BL-013 | OpenAI-compatible gateway proxy | AI Gateway | 2 |
| BL-014 | PII detection pipeline | Data Protection | 2 — Done (S4-28) |

## P2 — Medium

| ID | Item | Module | Phase |
|----|------|--------|-------|
| BL-020 | Audit log ingestion | Audit Explorer | 3 — Done (S4-33) |
| BL-021 | AG Grid audit table | Audit Explorer | 3 — Done (S4-31) |
| BL-037 | External SIEM audit connectors | Audit Explorer | 4 — Done (S4-38) |
| BL-022 | Compliance framework scoring engine | Compliance | 3 — Done (S4-29) |
| BL-023 | Prompt injection detection service | Security | 3 — Done (S4-32) |
| BL-024 | Studio prompt tester | Studio | 4 — Done (S5-02) |
| BL-025 | OpenTelemetry instrumentation | Observability | 3 |
| BL-026 | Policy Studio ↔ Governance Graph linking | Policy Studio | 3 |

## P3 — Low

| ID | Item | Module | Phase |
|----|------|--------|-------|
| BL-030 | Report PDF export (executive/governance templates) | Reports | 4 — Done (S4-02) |
| BL-034 | Scheduled report email delivery to recipients | Reports | 4 — Done (S4-03) |
| BL-035 | Celery report job runner (cron + generating status) | Reports | 4 — Done (S4-03) |
| BL-036 | Executive reporting PDF templates | Reports | 4 — Done (S4-02) |
| BL-031 | Kubernetes Helm chart | DevOps | 5 — Done (S4-35) |
| BL-032 | Air-gap offline bundle | DevOps | 5 — Done (S4-36) |
| BL-033 | Vault integration for secrets | Security | 5 — Done (S6-01) |

## P4 — Ops & Release (backlog)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-038 | Configure Git remote and push `main` | DevOps | — | Repo is local-only today |
| BL-039 | Run and stabilize full backend pytest suite (local + CI) | QA | — | Tests exist; prod Docker image has no pytest |
| BL-040 | Production env template — rotate JWT secret, enforce Vault | Security | 5 — Done (S6-06) |
| BL-041 | OIDC JIT provisioning toggle in Settings UI | Settings / Identity | 5c — Done (S6-05) |
| BL-042 | OIDC IdP group → PySetu role mapping | Identity | 5c — Done (S6-07) |
| BL-043 | SCIM user provisioning (optional) | Identity | 5c | Out of scope for Sprint 6 |
| BL-044 | Remove demo credentials from production bundles | Security | 5d | Phase 5d in OIDC design |
| BL-045 | Penetration test prep checklist + remediation backlog | Security | 5 | Pre-M5 gate |
| BL-046 | Update stale progress docs and roadmap milestones | Docs | — | Done (M1–M12 aligned Aug 13) |
| BL-047 | SAML 2.0 support | Identity | 6+ | Deferred from Phase 5 |
| BL-048 | Istio service mesh integration | DevOps | 6+ | Deferred from Phase 5 |

## Phase 6 — Enterprise Operations

| ID | Item | Module | Phase | Status |
|----|------|--------|-------|--------|
| BL-050 | LLM Router dynamic rule CRUD backend | LLM Router | 6 | Done |
| BL-051 | MCP live trust/risk scoring backend | MCP Governance | 6 | Done |
| BL-052 | Compliance framework live scoring engine | Compliance | 6 | Done |
| BL-053 | Platform billing / usage metering hooks | Platform | 6 | Done (audit `usage_metadata`; billing UI deferred) |
| BL-054 | Tenant self-service onboarding workflow | Platform | 6 | Done |
| BL-055 | SLA / uptime dashboards for operators | Observability | 6 | Done |

## Phase 7 — Gateway Pipeline Parity (planned)

> Full matrix: [gateway-parity-roadmap.md](./gateway-parity-roadmap.md)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-056 | AI traffic rate limits + token budgets (tenant/team/model) | Gateway | 7 | Done (Req/min/hr/day & TPM/TPH/TPD Redis limits + UI) |
| BL-057 | Per-user / per-team usage metering & attribution | Platform / Gateway | 7 | API key + OIDC subject tagging |
| BL-058 | Domain allowlists (login + API client origins) | Identity | 7 | Tenant policy in Settings |
| BL-059 | Response-path guardrails (egress scan parity) | Gateway / Security | 7 | Done (DLP scan, egress policy inspection & stream audit) |
| BL-060 | Routing groups — alias-as-model, weighted failover | LLM Router | 7 | Done (Entity, Migration 036, CRUD API, Router resolution, Auto-failover & Frontend UI) |
| BL-077 | Regional routing GA | LLM Router / UAG | 7–10 | Done Aug 13 — policy-bundle mapping to US/EU/India Bedrock + Vertex regions |

## Phase 8 — Prompt Lifecycle & Cost Optimization (planned)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-061 | Managed system prompt store & enforce mode | Prompt Lifecycle | 8 | Done (Schema, CRUD API, Versioning, Gateway Injection & Full UI in S10-01/S10-02/S10-03) |
| BL-062 | Custom intents — trainable content classifiers | Security / Policy | 8 | Done (Migration 038, Model, Service, Scan Engine, API & Policy Studio UI in S10-04/S10-05) |
| BL-063 | Token saving — JSON→TOON / payload compression | Gateway | 8 | Done (S11-01 engine + S11-02 dashboard before/after) |
| BL-064 | Dynamic tool calling — relevant MCP tools only | MCP Governance | 8 | Done (S11-03 ranking engine + gateway cap; S11-04 MCP Governance toggle & preview) |

## Phase 9 — MCP Platform & Deep Observability (complete Aug 13)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-065 | MCP multiplex — single gateway URL | MCP Governance | 9 | Done (S12-01: POST /v1/mcp JSON-RPC, server__tool routing, MCP Governance URL card) |
| BL-066 | MCP catalog — curated library + one-click install | MCP Governance | 9 | Done (S12-02: curated catalog, one-click install, custom transport URL) |
| BL-067 | MCP OAuth auth mediation / token broker | MCP Governance | 9 | Done (S12-03: vault-backed broker, client_credentials/refresh/static, inject Bearer on MCP calls) |
| BL-068 | Tool risk taxonomy (read/write/destructive) | MCP Governance | 9 | Done (S12-04: classify + hide overrides, auto-hide destructive, omitted from multiplex/dynamic/invoke) |
| BL-069 | Agent auto-detection + per-agent MCP toggles | MCP Governance | 9 | Done (S12-05: UA/metadata detect, tenant toggles, per-server allowlists, gateway filter) |
| BL-070 | Self-service MCP / AI portal | MCP Governance | 9 | Done (S12-06: portal browse/connect, per-user tokens, admin visibility) |
| BL-071 | Web search MCP + enterprise URL filtering | MCP Governance | 9 | Done (S12-07: allow/deny patterns, vendor hooks, gateway enforcement) |
| BL-072 | Per-user/team/model token & cost analytics | Observability | 9 | Done (S13-01: audit attribution API + dashboard card) |
| BL-073 | Full request/response log store | Audit Explorer | 9 | Done (S13-02: audit_log_bodies + retention + UI) |
| BL-074 | OTel-native trace replay | Observability | 9 | Done (S13-03: stage-by-stage replay from audit + OTel id) |
| BL-075 | Alert webhooks (Slack / ServiceNow) | Identity / Audit | 7 | Done (Delivery stubs, payload formatter, test alert API, rate limit & token budget breach alerts) |
| BL-076 | Telemetry facade API (`/telemetry/*`) | Backend | 9 | Dashboard/Monitoring single source |

## Phase 10 — Enterprise Security Parity (complete Aug 13; BL-079 optional)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-078 | Gateway SLA operator dashboard | Observability | 10 | Done Aug 13 — availability, p99, overhead, provider health, shared HTTP pool reuse |
| BL-079 | Endpoint agent — TLS inspect + DLP (macOS/Windows) | Security | 10+ | Optional separate deliverable |
| BL-080 | Red team testing suite | Security / QA | 10 | Done Aug 13 — adversarial campaigns + JSON/CSV reports |
| BL-081 | Claude.ai compliance API sync adapter | Compliance | 10 | Done Aug 13 — org/user/chat ingestion and DLP audit evidence; live provider pull remains deployment work |
| BL-082 | PHI / PCI / financial classifiers | Data Protection | 10 | Done Aug 13 — DLP redaction patterns + protected scan API; extend BL-014 |

## Phase 11 — HelixGuard Parity: LLM Router & MCP UX (active — Sprint 15/16)

> **Inspired by:** HelixGuard AI Dashboard review (Aug 13, 2026)  
> **Full analysis:** [helixguard_analysis_and_roadmap.md](../../.gemini/antigravity-ide/brain/24d5e7f0-0378-4184-9303-9163661c333e/helixguard_analysis_and_roadmap.md)

### Tier 1 — Strategic / High Impact

| ID | Item | Module | Sprint | Notes |
|----|------|--------|--------|-------|
| BL-083 | REST-to-MCP auto-proxy wizard (OpenAPI / Postman / GraphQL → MCP server) | MCP Governance | 15–16 | ✅ **Delivered** — `RestToMcpWizardModal` 3-step wizard: protocol → tool preview → RBAC assign → `createMcpServer`. Client-side parsers for OpenAPI, Postman, GraphQL. "Import from API spec" button in MCP Servers header. Backend spec-proxy endpoint `POST /mcp/servers/parse-spec` (Aug 13). |
| BL-084 | SSO context credential injection (OIDC token forwarded to MCP REST backends; LLM never sees keys) | MCP Governance / Security | 14 | ✅ **Delivered** — `McpSsoInjectionCard` in Access & RBAC tab. Per-server OIDC token injection config with header name, format, claim extract. Header preview live. Backend enforcement endpoint in Sprint 14. |
| BL-085 | Tool-level RBAC explicit deny lists (per RBAC group: allowed servers + denied individual tools) | MCP Governance | 13 | ✅ **Delivered** — `McpToolDenyListCard` in Access & RBAC tab; persists to localStorage; backend API in Sprint 15 |

### Tier 2 — High Value / Medium Effort

| ID | Item | Module | Sprint | Notes |
|----|------|--------|--------|-------|
| BL-086 | Enhanced visual routing engine (dynamic SVG fan-out, traffic %, cloud vs air-gapped badge, rule simulation mode) | LLM Router | 14 | ✅ **Delivered** — `RoutingVisualEngine` SVG component in `llm-router-view.tsx` |
| BL-087 | Per-rule response format configuration in UI (OpenAI / Anthropic / Vertex / Universal Auto-Negotiated) | LLM Router | 14 | ✅ **Delivered** — response format selector in `routing-rule-modal.tsx` + display in Rule Details panel |
| BL-088 | API key ↔ Routing Rule explicit binding view (assign/remove keys from within Rule Details panel) | LLM Router | 14 | ✅ **Delivered** — "Assigned API Keys" section in Rule Details panel reads from `getClientApiKeys` |
| BL-089 | MCP Governance alert feed (high-risk tool calls, unusual access patterns, server blocks — within MCP module) | MCP Governance | 13 | ✅ **Delivered** — Recent Alerts feed in MCP Overview tab (high risk + offline alerts) |
| BL-091 | Model performance tab in LLM Router (latency + throughput charts per model; cloud vs local comparison) | LLM Router | 14 | ✅ **Delivered** — Performance tab with latency area chart + throughput bar chart + per-model stat cards |

### Tier 3 — Quick Wins

| ID | Item | Module | Sprint | Notes |
|----|------|--------|--------|-------|
| BL-090 | Trust score fleet donut chart (Low/Medium/High distribution across all MCP servers) | MCP Governance | 13 | ✅ **Delivered** — Trust distribution donut in MCP Overview tab |
| BL-085 | Tool-level RBAC explicit deny lists (per RBAC group: allowed servers + denied individual tools) | MCP Governance | 13 | ✅ **Delivered** — `McpToolDenyListCard` in Access & RBAC tab; persists to localStorage; backend API in Sprint 15 |

## Phase 12 — Quality & shared primitives (Sprint 17)

> Verified plan: [quality-audit-sprint.md](./quality-audit-sprint.md)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-092 | Radix Dialog + replace duplicated `ModalShell` | Frontend | 12 | Done Aug 14 |
| BL-093 | Assign API key modal uses rule-binding APIs | LLM Router | 12 | Done Aug 14 — BL-088 follow-up |
| BL-094 | Shared `resolve_range()` in `app.core.date_range` | Backend | 12 | Done Aug 14 |
| BL-095 | App Router error UI | Frontend | 12 | Done Aug 14 |
| BL-096 | Loading / error / empty on four core views | Frontend | 12 | Done Aug 14 |
| BL-097 | LoginRequest min_length (password, tenant_slug) | Backend | 12 | Done Aug 14 |

## Phase 13 — MCP compliance pipeline (Sprint 18–20)

> Design: [mcp-policy-pipeline-design.md](./mcp-policy-pipeline-design.md) · Plan: [mcp-policy-pipeline-plan.md](./mcp-policy-pipeline-plan.md)

### Layer 1 — Enforcement (Sprint 18)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-098 | AuditLog on MCP `tools/call` (multiplex + chat) with `client_api_key_id` in metadata | MCP Gateway | 13 | Closes MCP-009 |
| BL-099 | Enforce `mcp_tool_deny_rules` on gateway `tools/list` + `tools/call` | MCP Gateway | 13 | Closes BL-085 / MCP-005 |
| BL-100 | `inspect_for_gateway` on MCP tool args + results (ingress/egress) | MCP Gateway | 13 | Same bundle path as chat |
| BL-101 | Policy bundle `mcp_scope` allowlist + shared `mcp_access_service` filter | Policy / MCP | 13 | Empty scope = all tenant MCP |
| BL-102 | Honor `routing_rule_client_keys` in `select_model` | LLM Router | 13 | BL-088 enforcement |
| BL-103 | Bundle MCP scope UI (server + optional tool picker) | Policy Studio | 13 | New bundles: allowlist default |

### Layer 2 — Compliance metadata (Sprint 19)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-104 | JWT `purpose` / `lawful_basis` claims → `compliance_metadata` on audit | Auth / Audit | 13 | Optional on client keys |
| BL-105 | MCP tool response redaction (DLP on tool results) | MCP Gateway | 13 | Beyond chat egress |

### Layer 3 — Framework packs (Sprint 20+)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-106 | Framework rule packs (GDPR/HIPAA/ISO/SOC2 config, not monolithic OPA) | Compliance | 13 | Spike then implement |
| BL-107 | Retention policies per framework + erasure workflow hooks | Compliance / Audit | 13 | HIPAA 6y, GDPR erasure |
| BL-108 | Optional immutable / WORM audit ledger export | Audit | 13 | Enterprise optional |

## Delivered (reference)

| ID | Item | Sprint / Notes |
|----|------|----------------|
| — | AI Gateway OpenAI/Gemini/Ollama proxy | S3 (supersedes BL-013 scope) |
| — | Reports catalog + CSV export + builder/scheduling UI | S3-01, S3-02, S3-02b |
| — | OpenTelemetry spans + trace IDs in audit | S3-05 / BL-025 |
| — | Policy Studio ↔ Governance Graph linking | S3-06 / BL-026 |
| — | Async report generation + generating status | S4-01 / BL-035 |
| — | Report PDF export + executive PDF templates | S4-02 / BL-030, BL-036 |
| — | Celery scheduler + scheduled email delivery | S4-03 / BL-034, BL-035 |
| — | Policy Studio React Flow canvas | S4-04 / BL-010 |
| — | LLM provider registry CRUD | S4-05 / BL-011 |
| — | MCP server CRUD + connection config | S4-06 / BL-012 |
| — | Policy rule persistence API | S4-07 / BL-010 follow-up |
| — | LLM provider API key in router modal | S4-08 |
| — | MCP live endpoint health checks | S4-09 |
| — | Routing rule target validation | S4-10 |
| — | Routing rule condition evaluator | S4-11 |
| — | MCP live tool discovery (tools/list) | S4-12 |
| — | Weighted LLM routing pool | S4-13 |
| — | Vault-ready secrets abstraction | S4-14 / BL-033 |
| — | Vault in Docker Compose | S4-15 |
| — | Live LLM provider metrics | S4-16 |
| — | MCP session lifecycle (initialize) | S4-17 |
| — | Traffic-based routing rebalance | S4-18 |
| — | MCP session reuse + tools/call | S4-19 |
| — | Vault deployment guide | S4-20 |
| — | MCP tool invoke UI | S4-21 |
| — | Vault AppRole auth | S4-22 / BL-033 |
| — | Scheduled routing rebalance | S4-23 |
| — | Policy bundles + client API keys + gateway binding | S4-25, S4-26 |
| — | Governance Graph per-key bundle visibility | S4-27 |
| — | DLP pipeline + Data Protection API | S4-28 / BL-014 |
| — | GitHub Actions CI (.github/workflows/ci.yml) | S4-37 |
| — | External SIEM connectors (JSON/CEF/NDJSON push + pull export) | S4-38 / BL-037 |
| — | Air-gap Ollama model export/import scripts | S4-39 |
| — | Settings route sub-pages + sidebar submenu | S5-01 |
| — | Studio live security scan + pre-flight prompt lab | S5-02 / BL-024 |
| — | Dashboard 30-day period-over-period KPI trends | S5-05 |
| — | OIDC/SSO discovery design doc | S5-03 |
| — | Slack / ServiceNow alert webhook stubs | S5-04 |
| — | Tenant white-label branding (name/logo/tagline) | S5-06 |
| — | Vault JWT bootstrap + status API | S6-01 / BL-033 |
| — | OIDC provider admin CRUD (Phase 5a) | S6-02 |
| — | OIDC PKCE login + callback JWT issuance | S6-03 |
| — | Auth rate limiting on login/token endpoints | S6-04 |
| — | Platform tenant management portal (SaaS) | Post-S6 |
| — | Product marketing site + tenant subdomain entry modes | Post-S6 |
| — | Public legal pages (terms, privacy, cookies, trust) | Post-S6 |
| — | Backend Ruff lint on full `app/` package in CI | S4-40 |
| — | Air-gap offline bundle (deploy/airgap) | S4-36 / BL-032 |
| — | Kubernetes Helm chart (deploy/helm/pysetu) | S4-35 / BL-031 |
| — | ABAC / OPA gateway policy integration | S4-34 |
| — | Audit log ingestion pipeline + Celery batch ingest | S4-33 / BL-020 |
| — | Prompt injection detection + Security Center API | S4-32 / BL-023 |
| — | Audit Explorer AG Grid + CSV export | S4-31 / BL-021 |
| — | Compliance evidence snapshots + export | S4-30 |
| — | Notification engine (sanitized alerts) | S4 |
| — | Tenant integration settings API | Phase 2 |
| — | Universal AI Gateway v1 + Compatibility Center | Aug 2026 / M7 |
| — | Monitoring hub + UI overlap consolidation | Aug 2026 |
| — | Compliance remediation API + dedicated compliance fetch | Aug 2026 |

## Phase 8 — GenAI DLP Gateway (in progress)

> Roadmap: [genai-dlp-gateway-roadmap.md](./genai-dlp-gateway-roadmap.md)

| ID | Item | Module | Phase | Status |
|----|------|--------|-------|--------|
| BL-098 | DLP sensitivity label mapping | Data Protection | 8.1 | Done |
| BL-099 | OPA data-movement Rego rules | Gateway / OPA | 8.2 | Done |
| BL-100 | RAG gateway API (stub → Pinecone) | RAG Gateway | 8.3 | Done |
| BL-101 | Conditional RAG orchestrator | RAG Gateway | 8.4 | Done (v1) |
| BL-102 | GenAI evidence bundle export UI | Compliance | 8.5 | Done |
| BL-103 | IaC evidence (Checkov) | Compliance | 8.6 | Done (static scanner v1) |
| BL-104 | Break-glass policy exemptions (time-bound, audited) | RAG Gateway / OPA | 8.7 | Done |
