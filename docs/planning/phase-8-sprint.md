# Phase 8 Sprint — Prompt Lifecycle & Cost Optimization

**Sprints:** 10–11 (planned)  
**Dates:** Feb 8 – Apr 4, 2027 (estimated)  
**Goal:** Prompt store, custom intents, token compression, dynamic MCP tool calling  
**Status:** **Planning**

> Parity matrix: [gateway-parity-roadmap.md](./gateway-parity-roadmap.md)  
> Prerequisites: Phase 7 metering (BL-057), routing groups (BL-060)

---

## Sprint 10 — Prompt store & custom intents

| ID | Task | Owner | Backlog | Acceptance |
|----|------|-------|---------|------------|
| S10-01 | Prompt store schema — versions, variables, enforce flag | Backend | BL-061 | API CRUD + audit on change |
| S10-02 | Gateway prompt injection — resolve version at ingress | Gateway | BL-061 | Enforce mode blocks ad-hoc prompts |
| S10-03 | Prompt store UI — Studio + Settings | Frontend | BL-061 | Edit templates with `{{var}}` preview |
| S10-04 | Custom intents MVP — embedding + policy hybrid | Backend | BL-062 | Train from samples; block/monitor/redact |
| S10-05 | Custom intents UI — Security / Policy Studio | Frontend | BL-062 | Upload samples, test, deploy |

**Sprint 10 exit:** Tenant enforces a system prompt version on a route; custom intent blocks a topic.

---

## Sprint 11 — Token saving & dynamic tool calling

| ID | Task | Owner | Backlog | Acceptance |
|----|------|-------|---------|------------|
| S11-01 | Token saving engine — JSON→TOON / strip markdown | Backend | BL-063 | Opt-in; responses untouched; metrics |
| S11-02 | Token saving dashboard — before/after on Dashboard | Frontend | BL-063, BL-072 | Show % savings per tenant |
| S11-03 | Dynamic tool calling — rank/filter MCP tools per request | Backend | BL-064 | ≤N tools sent to model; token KPI |
| S11-04 | Dynamic tool calling UI — MCP Governance config | Frontend | BL-064 | Toggle + preview token estimate |
| S11-05 | Compounding cost report — routing + tools + compression | Reports | BL-063, BL-064 | Executive summary section |

**Sprint 11 exit:** M9 — Cost & Prompt Parity milestone; MCP tool call token reduction measured.

---

## Success metrics

| Metric | Target |
|--------|--------|
| JSON token reduction | ≥30% on eligible structured inputs |
| MCP tool description tokens | ≥50% reduction vs. full catalog |
| Prompt enforce coverage | 100% on configured routes |

## Out of scope (Sprint 10–11)

- MCP marketplace catalog (BL-066) → Phase 9
- Endpoint agent (BL-079) → Phase 10+
