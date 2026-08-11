# Phase 5 Sprint — Production Hardening & Enterprise Identity

**Sprint:** 6 (Phase 5 kickoff)  
**Dates:** Sep 22 – Nov 2, 2026  
**Goal:** Vault production readiness, OIDC provider admin (Phase 5a), security hardening  
**Status:** **Sprint 6 complete** (Aug 11, 2026)

## Sprint Backlog

| ID | Task | Owner | Status |
|----|------|-------|--------|
| S6-01 | Vault production mode (JWT from Vault, status API) | Backend | Done |
| S6-02 | OIDC provider admin CRUD (Phase 5a — no login yet) | Full Stack | Done |
| S6-03 | OIDC login callback + JWT issuance (Phase 5b) | Backend | Done |
| S6-04 | Production JWT guard + rate limiting spike | Backend | Done |

## Phase 5 remainder (not in Sprint 6)

These items complete Phase 5 before M5 “Production Ready”:

| ID | Task | Owner | Status | Backlog |
|----|------|-------|--------|---------|
| S6-05 | OIDC JIT provisioning toggle in Settings UI | Full Stack | Done | BL-041 |
| S6-06 | Production env template + JWT secret rotation guide | DevOps | Done | BL-040 |
| S6-07 | OIDC group → role mapping (Phase 5c) | Backend | Done | BL-042 |
| S6-08 | Deprecate demo passwords in prod bundles (Phase 5d) | DevOps | **Next** | BL-044 |
| S6-09 | Penetration test prep checklist | Security | Planned | BL-045 |

## Phase 4 / Sprint 5 Recap (Complete)

All S5 items done: settings submenu, Studio security scan, OIDC design doc, alert webhooks, dashboard trends, tenant white-label.

## Backlog alignment

| Backlog | Item | Phase 5 plan |
|---------|------|--------------|
| BL-033 | Vault integration for secrets | S6-01 — **Done** |
| — | SSO/OIDC enterprise identity | S6-02 / S6-03 — **Done** |
| KI-005 | JWT secret dev default | S6-01 / S6-04 / **S6-06** |

## Out of scope (Phase 6+)

- Full SAML 2.0 (BL-047)
- SCIM provisioning (BL-043)
- Istio service mesh (BL-048)

## Where we left off

**Sprint 6 is done.** Phase 5 wrap-up continues with **S6-07** (OIDC group → role mapping), then S6-08–S6-09. See [phase-6-sprint.md](./phase-6-sprint.md) for Sprint 7 module backends.

Post-sprint work (platform portal, marketing site, legal pages) was delivered outside the Sprint 6 table; it is tracked in [backlog.md](./backlog.md) under Delivered.
