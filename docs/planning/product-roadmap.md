# Product Roadmap

## Vision

Build a commercial-grade Enterprise AI Control Plane competing with OpenRouter Enterprise, Lakera, Prompt Security, and QuirlAI-class gateways — with unique MCP governance, UAG protocol translation, and air-gapped deployment.

> **Competitive parity plan (Phases 7–10):** [gateway-parity-roadmap.md](./gateway-parity-roadmap.md)

## Phase 1 — Foundation (Current Sprint)

- [x] Project scaffolding (frontend, backend, Docker)
- [x] Documentation governance structure
- [x] Enterprise navigation shell with light/dark themes
- [x] Executive Dashboard with mock analytics (refined to 9-panel mockup)
- [x] Multi-tenant state management (Zustand)
- [x] JWT auth scaffolding (backend)
- [x] Real authentication flow (login page + AuthGuard)
- [x] TanStack Query dashboard API integration
- [x] Settings module basics
- [x] Rich UI mockups for 9 core modules
- [x] Database migrations (Alembic)
- [x] Tenant-scoped API middleware (JWT `tenant_id` on module APIs)

## Phase 2 — Core Governance

- [x] Policy Studio UI (tree + editor — mock data)
- [x] LLM Router UI (routing donut + rules — mock data)
- [x] MCP Governance UI (inventory + KPIs — mock data)
- [x] Data Protection UI (classification + map — mock data)
- [x] Governance Graph (React Flow, live API)
- [x] AI Gateway (OpenAI/Gemini/Ollama proxy + streaming)
- [x] Tenant integration settings (API keys per tenant)
- [x] Ollama local inference integration
- [x] Policy Studio interactive builder (React Flow drag-and-drop) — S4-04 / BL-010
- [x] LLM Router backend (dynamic rule CRUD, cost optimization) — BL-050
- [x] MCP Governance backend (registration, live trust/risk scoring) — BL-051
- [x] Data Protection (PII/DLP engine integration) — BL-014 / BL-082

## Phase 3 — Audit & Compliance

- [x] Audit Explorer UI (searchable table)
- [x] Compliance Center UI (framework cards)
- [x] AI Security Center UI (analytics)
- [x] Audit log API (tenant-scoped, from PostgreSQL)
- [x] Observability UI + overview/traces API
- [x] Audit Explorer AG Grid + full request/response trace — BL-021 / BL-073
- [x] Compliance Center backend (live framework scoring) — BL-052
- [x] OpenTelemetry real instrumentation (S3-05)

## Phase 4 — Studio & Analytics

- [x] Studio sandbox UI (prompt/policy/MCP testing — partial)
- [x] Reports catalog UI + executive summary API
- [x] Report builder, query editor, schedule config, delivery recipients
- [x] CSV export via report run API
- [x] Report PDF export (BL-030)
- [x] Scheduled report job runner — Celery/cron (BL-035)
- [x] Scheduled email delivery to recipients (BL-034)
- [x] Executive reporting PDF templates (BL-036)
- [x] Async "generating" report status workflow (BL-035)

## Phase 5 — Production

- [x] Air-gap deployment bundle (S4-36 / BL-032)
- [x] Kubernetes Helm charts (S4-35 / BL-031)
- [x] OPA policy integration (S4-34)
- [x] Hashicorp Vault secrets management (S6-01 / BL-033)
- [x] OIDC/SSO admin + PKCE login (S6-02 / S6-03)
- [x] Auth rate limiting (S6-04)
- [x] Platform tenant portal + marketing/subdomain entry (post-S6)
- [x] OIDC JIT toggle in Settings UI (S6-05 / BL-041)
- [x] Production JWT rotation guide + env template (S6-06 / BL-040)
- [x] OIDC group mapping in Settings UI (S6-07 / BL-042)
- [x] Penetration test prep checklist (S6-09) — [penetration-test-prep.md](../security/penetration-test-prep.md)

## Phase 6 — Enterprise Operations (complete)

- [x] Universal AI Gateway v1 (protocol translation, Compatibility Center, admin) — M7
- [x] Monitoring hub consolidation + UI overlap cleanup
- [x] LLM Router dynamic rule CRUD backend (BL-050)
- [x] MCP live trust/risk scoring backend (BL-051)
- [x] Compliance framework live scoring (BL-052)
- [x] Platform onboarding + invite emails + usage hooks (BL-054 / BL-053)
- [x] Operator SLA / health dashboards (BL-055)
- [x] Wire alert webhooks to gateway events — rate limit, token budget, latency, outage (BL-075) — S9-06 / S13-05 done

## Phase 7 — Gateway Pipeline Parity (complete)

_See [gateway-parity-roadmap.md](./gateway-parity-roadmap.md) · [phase-7-sprint.md](./phase-7-sprint.md)_

- [x] AI traffic rate limits — req/min/hr/day (BL-056) — S8-02 done
- [x] Token budgets per tenant, team, model (BL-056) — S8-03 done
- [x] Per-user / per-team usage metering & attribution (BL-057) — S8-01 done
- [x] Domain allowlists for login and API access (BL-058) — S8-04 done
- [x] Response-path guardrails parity (BL-059) — S8-05 done
- [x] Routing groups — group-as-model, weighted pools, auto-failover (BL-060) — S9-01–03 done
- [x] Regional routing groups (US/India, Bedrock, Vertex) — spike (BL-077) — S9-05 done

## Phase 8 — Prompt Lifecycle & Cost Optimization (complete)

_See [phase-8-sprint.md](./phase-8-sprint.md)_

- [x] Prompt store — versioned prompts, `{{variable}}` templates, enforce mode (BL-061) — S10-01–03 done
- [x] Custom intents — trainable / configurable content classifiers (BL-062) — S10-04–05 done
- [x] Token saving — JSON→TOON / payload compression (~43% target on eligible inputs) (BL-063) — S11-01–02 done
- [x] Dynamic tool calling — relevant MCP tools only per request (BL-064) — S11-03–05 done

## Phase 9 — MCP Platform & Deep Observability (complete — Sprint 13)

_See [phase-9-10-sprint.md](./phase-9-10-sprint.md)_

- [x] MCP multiplex — single gateway URL for all MCP traffic (BL-065) — S12-01 done
- [x] MCP catalog — curated library + one-click install + custom transport URL (BL-066) — S12-02 done
- [x] MCP OAuth auth mediation / token broker (BL-067) — S12-03 done
- [x] Tool risk taxonomy — read / write / destructive + auto-hide (BL-068)
- [x] Agent auto-detection + per-agent MCP toggles (BL-069)
- [x] Self-service MCP / AI portal for end users (BL-070)
- [x] Web search MCP + enterprise URL filtering (BL-071)
- [x] Per-user / team / model cost & token analytics (BL-072) — S13-01 done
- [x] Full request/response log store + search (BL-073) — S13-02 done
- [x] OTel-native trace replay (BL-074) — S13-03 done
- [x] Telemetry facade API (`/telemetry/summary`, `/operations`, `/security`, `/traces`) (BL-076) — S13-04 done
- [x] Live monitoring ops panel — requests, tokens, p50, blocks (BL-076) — S13-06 done

## Phase 10 — Enterprise Security Parity (complete — Sprint 14)

- [x] Red team testing suite — adversarial prompt campaigns and JSON/CSV export (BL-080) — S14-01 done Aug 13
- [x] PHI / PCI / financial data classifiers in DLP pipeline and scan API (BL-082) — S14-02 done Aug 13
- [x] Claude.ai compliance sync adapter (orgs, users, chats, DLP evidence) (BL-081) — S14-03 done Aug 13
- [x] Regional routing GA — policy-bundle routing for US/EU/India across Bedrock and Vertex (BL-077) — S14-04 done Aug 13
- [x] Gateway SLA operator dashboard — availability, p99 latency, overhead, provider health, pooling status (BL-078) — S14-05 done Aug 13
- [ ] Endpoint agent — TLS inspection + DLP (macOS/Windows) — optional track (BL-079) — S15+

## Phase 11 — HelixGuard Parity: LLM Router & MCP UX (complete — Sprint 15/16)

> **Inspired by:** HelixGuard AI dashboard analysis (Aug 13, 2026) — [full analysis doc](../../.gemini/antigravity-ide/brain/24d5e7f0-0378-4184-9303-9163661c333e/helixguard_analysis_and_roadmap.md)

_Delivered M12 scope:_

- [x] REST-to-MCP auto-proxy wizard + spec-proxy endpoint (BL-083)
- [x] SSO context credential injection (BL-084)
- [x] Tool-level RBAC explicit deny lists (BL-085)
- [x] Enhanced visual routing engine (BL-086)
- [x] Per-rule response format UI (BL-087)
- [x] API key ↔ routing rule binding (BL-088)
- [x] MCP Governance alert feed (BL-089)
- [x] Trust score fleet donut (BL-090)
- [x] Model performance tab in LLM Router (BL-091)

## Phase 12 — Quality, a11y, and shared primitives (complete — Sprint 17)

_See [quality-audit-sprint.md](./quality-audit-sprint.md) (audit reviewed Aug 14; inflated LOC claims discarded)._

- [x] Shared Radix Dialog; remove duplicated `ModalShell` (BL-092)
- [x] Finish API-key ↔ rule assign/unassign in the assign-key modal (BL-093 / BL-088 follow-up)
- [x] Single `resolve_range()` in `app.core.date_range` (BL-094)
- [x] App Router `error.tsx` / `global-error.tsx` (BL-095)
- [x] Loading / error / empty states on Audit Explorer, Compliance, Governance Graph, Monitoring (BL-096)
- [x] Login schema min_length on password and tenant slug (BL-097)

## Phase 14 — GenAI DLP Gateway (complete — Aug 14)

> Roadmap: [genai-dlp-gateway-roadmap.md](./genai-dlp-gateway-roadmap.md)

- [x] DLP sensitivity label mapping (BL-109)
- [x] OPA data-movement Rego rules (BL-110)
- [x] RAG gateway API with Pinecone adapter (BL-111)
- [x] Conditional RAG orchestrator (BL-112)
- [x] GenAI evidence bundle export UI (BL-113)
- [x] IaC evidence static scanner (BL-114)
- [x] Break-glass policy exemptions (BL-115)

## Phase 13 — MCP compliance pipeline (Sprint 18–20)

> Design: [mcp-policy-pipeline-design.md](./mcp-policy-pipeline-design.md)

### Layer 1 — Gateway enforcement (Sprint 18)

- [x] AuditLog on MCP `tools/call` with key metadata (BL-098)
- [x] Enforce tool deny lists on gateway multiplex (BL-099)
- [x] DLP inspect on MCP tool args and results (BL-100)
- [x] Policy bundle `mcp_scope` + `mcp_access_service` (BL-101)
- [x] Routing rules honor assigned client API keys (BL-102)
- [ ] Bundle MCP scope UI (BL-103)

### Layer 2 — Compliance metadata (Sprint 19)

- [ ] JWT purpose / lawful_basis on audit rows (BL-104)
- [ ] MCP tool response redaction (BL-105)

### Layer 3 — Framework packs (Sprint 20+)

- [ ] Framework rule packs (BL-106)
- [ ] Retention + erasure workflows (BL-107)
- [ ] Optional WORM audit ledger (BL-108)

## Milestones

| Milestone | Target | Status |
|-----------|--------|--------|
| M1: Foundation Complete | Sprint 1 | ✅ Complete |
| M2: Core Modules MVP | Sprint 3 | ✅ Complete (~UI + partial API) |
| M3: Audit & Compliance | Sprint 5 | ✅ Complete (~UI + ingestion APIs) |
| M4: Studio & Reports | Sprint 5 | ✅ Complete |
| M5: Production Ready | Sprint 6 | ✅ Complete — Phase 5 (S6-01–09) |
| M6: Enterprise Operations | Sprint 7 | ✅ Complete — Phase 6 |
| M7: Universal AI Gateway v1 | Aug 2026 | ✅ Complete |
| M8: Gateway Pipeline Parity | Sprint 9 | ✅ Complete — BL-056–BL-060 (Aug 12) |
| M9: Cost & Prompt Parity | Sprint 11 | ✅ Complete — BL-061–BL-064 (Aug 13) |
| M10: MCP Platform & Observability | Sprint 13 | ✅ Complete Aug 13 — BL-065–BL-076 |
| M11: Enterprise Security Parity | Sprint 14+ | ✅ Complete Aug 13 — BL-077–BL-082 (BL-079 optional) |
| M12: HelixGuard Parity — LLM Router & MCP UX | Sprint 15–16 | ✅ Complete — BL-083–BL-091 delivered; BL-079 remains optional (Aug 13, 2026) |
| M13: Quality & shared UI primitives | Sprint 17 | ✅ Complete Aug 14 — BL-092–BL-097 ([quality-audit-sprint.md](./quality-audit-sprint.md)) |
| M14: MCP compliance pipeline | Sprint 18–20 | 🔄 In progress — BL-098–BL-108 ([mcp-policy-pipeline-design.md](./mcp-policy-pipeline-design.md)) |
| M15: GenAI DLP Gateway | Aug 14, 2026 | ✅ Complete — BL-109–BL-115 ([genai-dlp-gateway-roadmap.md](./genai-dlp-gateway-roadmap.md)) |
