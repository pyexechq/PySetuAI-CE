# Phase 5 Sprint — Production Hardening & Enterprise Identity

**Sprint:** 6 (Phase 5 kickoff)  
**Dates:** Sep 22 – Nov 2, 2026  
**Goal:** Vault production readiness, OIDC provider admin (Phase 5a), security hardening

## Sprint Backlog

| ID | Task | Owner | Status |
|----|------|-------|--------|
| S6-01 | Vault production mode (JWT from Vault, status API) | Backend | Done |
| S6-02 | OIDC provider admin CRUD (Phase 5a — no login yet) | Full Stack | Done |
| S6-03 | OIDC login callback + JWT issuance (Phase 5b) | Backend | Done |
| S6-04 | Production JWT guard + rate limiting spike | Backend | Done |

## Phase 4 / Sprint 5 Recap (Complete)

All S5 items done: settings submenu, Studio security scan, OIDC design doc, alert webhooks, dashboard trends, tenant white-label.

## Backlog alignment

| Backlog | Item | Phase 5 plan |
|---------|------|--------------|
| BL-033 | Vault integration for secrets | S6-01 |
| — | SSO/OIDC enterprise identity | S6-02 / S6-03 |
| KI-005 | JWT secret dev default | S6-01 / S6-04 |

## Next Actions

1. Finish Vault status UI + JWT bootstrap (S6-01)
2. OIDC provider settings page (S6-02)
3. OIDC authorize/callback flow (S6-03)

## Out of scope (later Phase 5)

- Full SAML 2.0
- SCIM provisioning
- Penetration test remediation
- Istio service mesh
