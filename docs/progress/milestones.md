# Milestones

| ID | Milestone | Description | Target | Status |
|----|-----------|-------------|--------|--------|
| M1 | Project Foundation | Scaffolding, docs, navigation, dashboard | Aug 2026 | Complete |
| M2 | Authentication & Multi-Tenancy | JWT login, RBAC, tenant isolation | Aug 2026 | In Progress (~85%) |
| M3 | Core Governance Modules | Policy Studio, LLM Router, MCP Governance | Sep 2026 | UI Mockups Done |
| M4 | Audit & Compliance | Audit Explorer, Compliance Center, Security | Oct 2026 | UI Mockups Done |
| M5 | Studio & Analytics | Sandbox testing, reports, UAG simulator | Nov 2026 | In Progress (~55%) |
| M6 | Production Ready | K8s, air-gap, hardening | Dec 2026 | In Progress |
| M7 | Universal AI Gateway v1 | Protocol translation, Compatibility Center | Aug 2026 | Complete |
| M8 | Gateway Pipeline Parity | Rate limits, budgets, routing groups, failover | Sprint 9 | Planned |
| M9 | Cost & Prompt Parity | Prompt store, token saving, dynamic tool calling | Sprint 11 | Planned |
| M10 | MCP Platform & Observability | Catalog, multiplex, per-user analytics, trace replay | Sprint 13 | Planned |
| M11 | Enterprise Security Parity | Red team, PHI/PCI, regional routing, SLA | Sprint 14+ | Planned |

> Parity detail: [gateway-parity-roadmap.md](../planning/gateway-parity-roadmap.md)

## M1 Detail — Project Foundation

### Done
- [x] Monorepo structure
- [x] Frontend with Next.js App Router
- [x] Executive Dashboard (refined with 9-panel mockup KPIs)
- [x] Enterprise navigation (14 modules incl. Governance Graph)
- [x] Theme support
- [x] Backend FastAPI scaffold
- [x] Docker Compose
- [x] Documentation governance
- [x] Login page + client-side AuthGuard
- [x] TanStack Query dashboard API integration
- [x] Settings module basics
- [x] Rich UI for 9 mockup modules (mock data)

### UAG v1 + UI consolidation (Aug 11, 2026)
- [x] Backend module, migration, API, gateway hooks
- [x] Compatibility Center UI
- [x] Studio translation simulator
- [x] Monitoring hub (Security + Observability merge)
- [x] UI overlap consolidation (Tiers 1–3)
- [x] Compliance dedicated API
- [x] Documentation and test plan

### Parity roadmap (Phases 7–10)
- [ ] Gateway pipeline — BL-056–BL-060 ([gateway-parity-roadmap.md](../planning/gateway-parity-roadmap.md))
- [ ] Prompt & cost — BL-061–BL-064
- [ ] MCP platform & observability — BL-065–BL-076
- [ ] Enterprise security — BL-077–BL-082

### Remaining
- [ ] Server-side tenant middleware on all future module APIs
- [ ] Module backend APIs (Phase 2)
