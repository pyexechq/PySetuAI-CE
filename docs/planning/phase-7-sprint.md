# Phase 7 Sprint — Gateway Pipeline Parity

**Sprints:** 8–9 (planned)  
**Dates:** Dec 15, 2026 – Feb 7, 2027 (estimated)  
**Goal:** Rate limits, usage metering, routing groups with failover — match enterprise gateway “pipeline” expectations  
**Status:** **Planning** — starts after Phase 6 (S7) module backends

> Parity matrix: [gateway-parity-roadmap.md](./gateway-parity-roadmap.md)  
> Prerequisites: BL-053 usage hooks (metering foundation), BL-050 router CRUD

---

## Sprint 8 — Traffic control & attribution

| ID | Task | Owner | Backlog | Acceptance | Status |
|----|------|-------|---------|------------|--------|
| S8-01 | Usage metering hooks — tag requests by user, team, API key | Backend | BL-057, BL-053 | Every gateway audit row has actor + key + token counts | Done |
| S8-02 | AI rate limits — req/min/hr/day per tenant | Backend | BL-056 | 429 with Retry-After; Redis-backed | Done |
| S8-03 | Token budgets — tenant / team / model caps | Backend | BL-056 | Block or alert when budget exceeded | Done |
| S8-04 | Domain allowlists — login + API origins | Full Stack | BL-058 | Settings UI + enforce on auth/gateway | Done |
| S8-05 | Response-path guardrails — egress scan on completions | Backend | BL-059 | UAG + gateway response pipeline parity | Done |
| S8-06 | Settings UI — limits & budgets admin | Frontend | BL-056, BL-058 | Tenant admin can configure without code | Done |

**Sprint 8 exit:** Demo tenant hits rate limit; budget alert fires; domain block on disallowed origin.

---

## Sprint 9 — Routing groups & regional spike

| ID | Task | Owner | Backlog | Acceptance | Status |
|----|------|-------|---------|------------|--------|
| S9-01 | Routing group entity — name, members, weights | Backend | BL-060 | CRUD API + DB migration | Done |
| S9-02 | Group-as-model — `model: "production"` resolves group | Gateway | BL-060 | OpenAI-compatible model param | Done |
| S9-03 | Auto-failover — try next provider on 5xx/timeout | Gateway | BL-060 | Audit log records failover chain | Done |
| S9-04 | LLM Router UI — routing groups tab | Frontend | BL-060 | Create/edit groups, weights, members | Done |
| S9-05 | Regional routing spike — Bedrock + Vertex adapters | Backend | BL-077 | One route per cloud; design doc | Done |
| S9-06 | Wire alert webhooks — budget + rate limit breaches | Backend | BL-075 | Closes DEF-004 partial | Done |

**Sprint 9 exit:** M8 — Gateway Pipeline Parity milestone (COMPLETE).

---

## Dependencies

- S8-01 before S8-03 and BL-072 (Phase 9 analytics)
- BL-050 (LLM Router CRUD) should land in S7 or early S8 before S9-01
- BL-075 can start in S7 but must complete by S9-06

## Out of scope (Sprint 8–9)

- Prompt store (BL-061) → Phase 8
- Dynamic tool calling (BL-064) → Phase 8
- MCP catalog (BL-066) → Phase 9
