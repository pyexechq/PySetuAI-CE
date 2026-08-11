# Current Sprint — Phase 5 Wrap-up → Phase 6 Kickoff

**Sprint:** 7 (starting after Phase 5 remainder)  
**Dates:** Nov 3 – Dec 14, 2026 (planned)  
**Active focus:** **S6-09** — Penetration test prep checklist

> Phase 5 plan: [phase-5-sprint.md](./phase-5-sprint.md)  
> Phase 6 plan: [phase-6-sprint.md](./phase-6-sprint.md)  
> Full backlog: [backlog.md](./backlog.md)

## Phase 5 wrap-up queue

| ID | Task | Status |
|----|------|--------|
| S6-05 | OIDC JIT provisioning toggle in Settings UI | Done |
| S6-06 | Production env template + JWT rotation guide | Done |
| **S6-07** | **OIDC group → role mapping** | **Done** |
| S6-08 | Remove demo credentials from prod bundles | **Done** |
| S6-09 | Penetration test prep checklist | Planned |

## Ops backlog (non-blocking)

| ID | Item |
|----|------|
| BL-038 | Configure Git remote and push |
| BL-039 | Stabilize pytest in CI/local |
| BL-046 | Refresh progress docs / roadmap |

## Phase 6 preview (Sprint 7)

Starts after S6-08–S6-09:

- S7-01 LLM Router backend CRUD (BL-050)
- S7-02 MCP live trust/risk scoring (BL-051)
- S7-03 Compliance live scoring (BL-052)
- S7-04 Wire alert webhooks — start (BL-075 / DEF-004)

## Phases 7–10 — Competitive parity (planned)

Full enterprise gateway parity (rate limits, prompt store, dynamic MCP tools, MCP catalog, per-user cost analytics, red team, etc.):

- [gateway-parity-roadmap.md](./gateway-parity-roadmap.md) — master matrix + milestones M8–M11
- [phase-7-sprint.md](./phase-7-sprint.md) — Sprints 8–9
- [phase-8-sprint.md](./phase-8-sprint.md) — Sprints 10–11
- [phase-9-10-sprint.md](./phase-9-10-sprint.md) — Sprints 12–14+

See [phase-6-sprint.md](./phase-6-sprint.md) for current sprint detail.

## Production references (S6-06)

- [`.env.production.example`](../.env.production.example)
- [JWT secret rotation](../security/jwt-secret-rotation.md)
- `./scripts/generate-jwt-secret.sh` · `./scripts/vault-bootstrap-jwt-secret.sh`
