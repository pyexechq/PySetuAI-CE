# Phase 6 Sprint — Enterprise Operations & Module Backend

**Sprint:** 7 (Phase 6)  
**Dates:** Aug 2026  
**Goal:** Close Phase 2/3 backend gaps, extend platform operations, prepare for M5 production gate  
**Status:** **Complete** (Aug 11, 2026)

> Phase 5 completion: [phase-5-sprint.md](./phase-5-sprint.md)

## Prerequisites (Phase 5 wrap-up)

| ID | Task | Status |
|----|------|--------|
| S6-05 | OIDC JIT provisioning toggle in Settings UI | Done |
| S6-06 | Production env template + JWT rotation | Done |
| S6-07 | OIDC group → role mapping | Done |
| S6-08 | Remove demo credentials from prod bundles | Planned |
| S6-09 | Penetration test prep | Done — [penetration-test-prep.md](../security/penetration-test-prep.md) |

## Sprint 7 deliverables

| ID | Task | Status | Backlog |
|----|------|--------|---------|
| S7-01 | LLM Router dynamic rule CRUD API + UI wiring | Done | BL-050 |
| S7-02 | MCP trust/risk scoring backend (live metrics) | Done | BL-051 |
| S7-03 | Compliance framework live scoring engine | Done | BL-052 |
| S7-04 | Platform tenant onboarding polish (invite flow, docs) | Done | BL-054 |
| S7-05 | Operator SLA / health dashboard | Done | BL-055 |
| S7-06 | Usage metering hooks on gateway audit logs | Done | BL-053 |
| S7-07 | Customizable admin invite email templates | Done | BL-054 |

## Phase 6 themes (delivered)

1. **Module backend completion** — LLM Router CRUD, MCP live scoring, Compliance live scoring.
2. **Platform operations** — tenant invites, email templates, ops/usage dashboards, feature entitlements.
3. **Production gate prep** — pen-test checklist, health probes (DB + OPA), real observability latency.

## Key docs & routes

- Onboarding: [tenant-onboarding.md](../platform/tenant-onboarding.md)
- Platform portal: `/platform`, `/platform/ops`, `/platform/tenants/new`
- Accept invite: `/accept-invite?token=…`
- APIs: `/platform/ops/overview`, `/platform/usage/overview`, `/platform/invite-email/*`

## Out of scope (deferred)

- SAML 2.0 (BL-047), SCIM (BL-043), full billing/invoicing (BL-053 billing UI)
- Gateway parity BL-056+ — see [phase-7-sprint.md](./phase-7-sprint.md)

## Milestone

| Milestone | Status | Notes |
|-----------|--------|-------|
| M5: Production Ready | In progress | Phase 6 complete; pen-test execution + BL-038 remote remain |
