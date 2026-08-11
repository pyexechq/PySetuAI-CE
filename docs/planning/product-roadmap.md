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
- [ ] Tenant-scoped API middleware (for Phase 2 module APIs)

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
- [ ] LLM Router backend (dynamic rule CRUD, cost optimization)
- [ ] MCP Governance backend (registration, live trust/risk scoring)
- [ ] Data Protection (PII/DLP engine integration)

## Phase 3 — Audit & Compliance

- [x] Audit Explorer UI (searchable table)
- [x] Compliance Center UI (framework cards)
- [x] AI Security Center UI (analytics)
- [x] Audit log API (tenant-scoped, from PostgreSQL)
- [x] Observability UI + overview/traces API
- [ ] Audit Explorer AG Grid + full request/response trace
- [ ] Compliance Center backend (live framework scoring)
- [x] OpenTelemetry real instrumentation (S3-05)

## Phase 4 — Studio & Analytics

- [x] Studio sandbox UI (prompt/policy/MCP testing — partial)
- [x] Reports catalog UI + executive summary API
- [x] Report builder, query editor, schedule config, delivery recipients
- [x] CSV export via report run API
- [ ] Report PDF export (BL-030)
- [ ] Scheduled report job runner — Celery/cron (BL-035)
- [ ] Scheduled email delivery to recipients (BL-034)
- [ ] Executive reporting PDF templates (BL-036)
- [ ] Async "generating" report status workflow (BL-035)

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
- [x] Wire alert webhooks to gateway events (BL-075)

## Phase 7 — Gateway Pipeline Parity (planned)

_See [gateway-parity-roadmap.md](./gateway-parity-roadmap.md) · [phase-7-sprint.md](./phase-7-sprint.md)_

- [ ] AI traffic rate limits — req/min/hr/day (BL-056)
- [ ] Token budgets per tenant, team, model (BL-056)
- [ ] Per-user / per-team usage metering & attribution (BL-057)
- [ ] Domain allowlists for login and API access (BL-058)
- [ ] Response-path guardrails parity (BL-059)
- [ ] Routing groups — group-as-model, weighted pools, auto-failover (BL-060)
- [ ] Regional routing groups (US/India, Bedrock, Vertex) — spike (BL-077)

## Phase 8 — Prompt Lifecycle & Cost Optimization (planned)

_See [phase-8-sprint.md](./phase-8-sprint.md)_

- [ ] Prompt store — versioned prompts, `{{variable}}` templates, enforce mode (BL-061)
- [ ] Custom intents — trainable / configurable content classifiers (BL-062)
- [ ] Token saving — JSON→TOON / payload compression (~43% target on eligible inputs) (BL-063)
- [ ] Dynamic tool calling — relevant MCP tools only per request (BL-064)

## Phase 9 — MCP Platform & Deep Observability (planned)

- [ ] MCP multiplex — single gateway URL for all MCP traffic (BL-065)
- [ ] MCP catalog — curated library + one-click install + custom transport URL (BL-066)
- [ ] MCP OAuth auth mediation / token broker (BL-067)
- [ ] Tool risk taxonomy — read / write / destructive + auto-hide (BL-068)
- [ ] Agent auto-detection + per-agent MCP toggles (BL-069)
- [ ] Self-service MCP / AI portal for end users (BL-070)
- [ ] Web search MCP + enterprise URL filtering (Zscaler/FortiGate/Cisco) (BL-071)
- [ ] Per-user / team / model cost & token analytics (BL-072)
- [ ] Full request/response log store + search (BL-073)
- [ ] OTel-native trace replay (BL-074)
- [ ] Telemetry facade API (`/telemetry/summary`, `/operations`, `/security`, `/traces`) (BL-076)

## Phase 10 — Enterprise Security Parity (planned)

- [ ] Red team testing suite — adversarial prompt campaigns (BL-080)
- [ ] PHI / PCI / financial data classifiers (BL-082)
- [ ] Claude.ai compliance API sync (orgs, users, chats, DLP) (BL-081)
- [ ] Gateway SLA metrics — overhead p99, uptime, connection pooling (BL-078)
- [ ] Endpoint agent — TLS inspection + DLP (macOS/Windows) — optional track (BL-079)

## Milestones

| Milestone | Target | Status |
|-----------|--------|--------|
| M1: Foundation Complete | Sprint 1 | Complete |
| M2: Core Modules MVP | Sprint 3 | Complete (~UI + partial API) |
| M3: Audit & Compliance | Sprint 5 | Complete (~UI + ingestion APIs) |
| M4: Studio & Reports | Sprint 5 | Complete |
| M5: Production Ready | Sprint 10 | In Progress — Phase 5 wrap-up (S6-08+) |
| M6: Enterprise Operations | Sprint 7 | Planned — see phase-6-sprint.md |
| M7: Universal AI Gateway v1 | Aug 2026 | Complete |
| M8: Gateway Pipeline Parity | Sprint 9 | Planned — BL-056–BL-060 |
| M9: Cost & Prompt Parity | Sprint 11 | Planned — BL-061–BL-064 |
| M10: MCP Platform & Observability | Sprint 13 | Planned — BL-065–BL-076 |
| M11: Enterprise Security Parity | Sprint 14+ | Planned — BL-077–BL-082 |
