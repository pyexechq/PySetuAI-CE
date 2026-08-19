# Known Issues

| ID | Issue | Severity | Module | Status |
|----|-------|----------|--------|--------|
| KI-001 | Dashboard falls back to mock data when API unavailable | Low | Dashboard | Mitigated — TanStack Query wired with fallback |
| KI-003 | No database migrations applied yet | Medium | Backend | Resolved |
| KI-002 | Auth uses client-side guard only (no middleware) | Low | Auth | Mitigated — Next.js middleware added |
| KI-004 | Module pages use mock data (no backend APIs) | Expected | All Modules | Open — Phase 2 |
| KI-005 | JWT secret uses dev default | High | Security | Mitigated — prod guard + rotation guide (S6-06); set secret before deploy |
| KI-006 | RBAC enforced client-side only | Medium | Auth | Mitigated — backend RBAC module, API permission checks, sidebar nav filtering, Settings user management UI |
| KI-007 | Recharts Pie label TypeScript warnings possible | Low | Dashboard | Monitoring |
| KI-009 | Port 8001 may be shadowed by a stale local uvicorn (IPv4) while Docker holds IPv6 — causes 404 on new endpoints via `127.0.0.1` | Low | DevOps | Resolved Aug 13 — kill stale `uvicorn app.main:app --port 8001` process, then `docker restart pysetuai-backend-1` |

## Resolution Plan

- KI-003: Address in Sprint 1 remaining task (Alembic)
- KI-005: Vault enabled by default in Docker Compose; rotate JWT and use AppRole before production — **Mitigated** (S6-01 + S6-06 rotation runbook)
- KI-002: Next.js middleware planned for Phase 1 completion
- KI-008: React Flow integration planned for Phase 2

## Resolved

- ~~KI-001 Dashboard uses mock data, not live API~~ — TanStack Query hook added with API integration
- ~~KI-004 Module pages are placeholders~~ — 9 rich module UIs implemented
