# Phase 6 Sprint — Enterprise Operations & Module Backend

**Sprint:** 7 (Phase 6 kickoff)  
**Dates:** Nov 3 – Dec 14, 2026 (planned)  
**Goal:** Close Phase 2/3 backend gaps, extend platform operations, prepare for M5 production gate  
**Status:** **Planning** — not started; Phase 5 wrap-up (S6-05–S6-09) runs first

> Phase 5 completion: [phase-5-sprint.md](./phase-5-sprint.md)

## Prerequisites (finish Phase 5 first)

| ID | Task | Status |
|----|------|--------|
| S6-05 | OIDC JIT provisioning toggle in Settings UI | Next |
| S6-06 | Production env template + JWT rotation | Done |
| S6-07 | OIDC group → role mapping | Planned |
| S6-08 | Remove demo credentials from prod bundles | Planned |
| S6-09 | Penetration test prep | Planned |

## Sprint 7 backlog (draft)

| ID | Task | Owner | Status | Backlog |
|----|------|-------|--------|---------|
| S7-01 | LLM Router dynamic rule CRUD API + UI wiring | Full Stack | Planned | BL-050 |
| S7-02 | MCP trust/risk scoring backend (live metrics) | Backend | Planned | BL-051 |
| S7-03 | Compliance framework live scoring engine | Backend | Planned | BL-052 |
| S7-04 | Platform tenant onboarding polish (invite flow, docs) | Full Stack | Planned | BL-054 |
| S7-05 | Operator SLA / health dashboard | Full Stack | Planned | BL-055 |

## Phase 6 themes

1. **Module backend completion** — replace remaining mock/placeholder API paths (LLM Router, MCP scoring, Compliance scoring).
2. **Platform operations** — extend SaaS portal beyond provision CRUD (onboarding, usage hooks).
3. **Production gate** — pen-test remediation, no demo secrets in prod, CI test stability (BL-038–BL-039, BL-045).

## Out of scope (Phase 6)

- SAML 2.0 (BL-047)
- SCIM (BL-043) — unless pulled forward from Phase 5c
- Full billing/invoicing (BL-053) — metering hooks only in S7; invoicing deferred
- Gateway parity items BL-056+ — see [phase-7-sprint.md](./phase-7-sprint.md)

## Follow-on phases (parity)

| Phase | Doc | Milestone |
|-------|-----|-----------|
| 7 — Pipeline parity | [phase-7-sprint.md](./phase-7-sprint.md) | M8 |
| 8 — Prompt & cost | [phase-8-sprint.md](./phase-8-sprint.md) | M9 |
| 9–10 — MCP & security | [phase-9-10-sprint.md](./phase-9-10-sprint.md) | M10, M11 |
| Full matrix | [gateway-parity-roadmap.md](./gateway-parity-roadmap.md) | — |

## Milestone target

| Milestone | Target | Dependency |
|-----------|--------|------------|
| M5: Production Ready | Sprint 10 | Phase 5 complete + S7 module backends + pen-test pass |

## Open decisions

1. Prioritize S7-01 (LLM Router) vs S7-03 (Compliance scoring) first?
2. Pull SCIM (BL-043) into Phase 6 or keep deferred?
3. Billing metering (BL-053) — required before first commercial pilot?
