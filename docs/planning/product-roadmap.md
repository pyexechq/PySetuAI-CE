# Product Roadmap

## Vision

Build a commercial-grade Enterprise AI Control Plane competing with OpenRouter Enterprise, Lakera, and Prompt Security while offering unique MCP governance and air-gapped deployment.

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

- [ ] Air-gap deployment bundle
- [ ] Kubernetes Helm charts
- [ ] OPA policy integration
- [ ] Hashicorp Vault secrets management
- [ ] Production hardening & penetration testing

## Milestones

| Milestone | Target | Status |
|-----------|--------|--------|
| M1: Foundation Complete | Sprint 1 | Complete |
| M2: Core Modules MVP | Sprint 3 | In Progress (~70%) |
| M3: Audit & Compliance | Sprint 5 | In Progress (~50%) |
| M4: Studio & Reports | Sprint 7 | In Progress (~40%) |
| M5: Production Ready | Sprint 10 | Planned |
