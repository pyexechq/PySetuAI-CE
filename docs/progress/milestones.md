# Milestones

| ID | Milestone | Description | Target | Status |
|----|-----------|-------------|--------|--------|
| M1 | Project Foundation | Scaffolding, docs, navigation, dashboard | Aug 2026 | Complete |
| M2 | Authentication & Multi-Tenancy | JWT login, RBAC, tenant isolation | Aug 2026 | Complete |
| M3 | Core Governance Modules | Policy Studio, LLM Router, MCP Governance | Sep 2026 | Complete |
| M4 | Audit & Compliance | Audit Explorer, Compliance Center, Security | Oct 2026 | Complete |
| M5 | Studio & Analytics | Sandbox testing, reports, UAG simulator | Nov 2026 | Complete |
| M6 | Production Ready | K8s, air-gap, hardening | Dec 2026 | Complete |
| M7 | Universal AI Gateway v1 | Protocol translation, Compatibility Center | Aug 2026 | Complete |
| M8 | Gateway Pipeline Parity | Rate limits, budgets, routing groups, failover | Sprint 9 | Complete |
| M9 | Cost & Prompt Parity | Prompt store, token saving, dynamic tool calling | Sprint 11 | Complete |
| M10 | MCP Platform & Observability | Catalog, multiplex, per-user analytics, trace replay | Sprint 13 | Complete (S13-01–06, Aug 13) |
| M11 | Enterprise Security Parity | Red team, PHI/PCI, regional routing, SLA | Sprint 14+ | Complete (S14-01–05; Aug 13, optional endpoint agent excluded) |
| M12 | HelixGuard Parity | REST-to-MCP, SSO injection, visual routing, deny lists | Sprint 15–16 | Complete (BL-083–BL-091; Aug 13) |
| M13 | Quality & shared primitives | Radix Dialog, date_range, error UI, query states | Sprint 17 | Complete (BL-092–BL-097; Aug 14) |
| M14 | MCP compliance pipeline | Policy bundle MCP scope, gated audit path, framework packs | Sprint 18–20 | In progress — [mcp-policy-pipeline-design.md](../planning/mcp-policy-pipeline-design.md) |
| M15 | GenAI DLP Gateway | Sensitivity labels, OPA data-movement, governed RAG, evidence bundles, exemptions | Aug 14, 2026 | Complete — [genai-dlp-gateway-roadmap.md](../planning/genai-dlp-gateway-roadmap.md) |
| M16 | Compliance UX & config | Tabbed Compliance Center, IaC/data-movement config UI, Reports preview, Help fixes, Vault default-on | Aug 15, 2026 | Complete — [aug-15-compliance-ux-update.md](./aug-15-compliance-ux-update.md) |

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

### Parity roadmap (Phases 7–11)
- [x] Gateway pipeline — BL-056–BL-060
- [x] Prompt & cost — BL-061–BL-064
- [x] MCP platform & observability — BL-065–BL-076
- [x] Enterprise security — BL-077–BL-082 (BL-079 optional)
- [x] HelixGuard LLM Router & MCP UX — BL-083–BL-091

### Remaining (out of product feature scope)
- [ ] Endpoint agent — TLS inspect + DLP desktop (BL-079, optional)
- [ ] Ops: git push / CI pytest / demo-credential strip (BL-038, BL-039, BL-044)
