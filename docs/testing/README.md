# Testing Strategy

## Current State

Phase 1 foundation — no automated tests yet. Manual verification via dev server and build.

## Planned Test Layers

### Frontend

| Type | Tool | Scope |
|------|------|-------|
| Unit | Vitest | Utils, stores, formatters |
| Component | Vitest + Testing Library | UI components, dashboard widgets |
| E2E | Playwright | Navigation, dashboard rendering, theme toggle |

### Backend

| Type | Tool | Scope |
|------|------|-------|
| Unit | pytest | Security utils, schemas |
| Integration | pytest + httpx | API endpoints, auth flow |
| Database | pytest + testcontainers | Model CRUD, tenant isolation |

## Test Plan — Phase 1 Completion

- [ ] Frontend builds without errors (`npm run build`)
- [ ] Backend starts and health check returns 200
- [ ] All 14 routes render without crash
- [ ] Theme toggle works in light and dark mode
- [ ] Sidebar navigation links route correctly
- [ ] Dashboard charts render with mock data

## Test Plan — Phase 2

- [ ] Login flow end-to-end
- [ ] JWT token validation on protected routes
- [ ] Tenant isolation (user A cannot access tenant B data)
- [ ] Policy CRUD operations
- [ ] LLM routing rule evaluation

## CI Pipeline (Planned)

```yaml
# GitHub Actions
- lint (eslint, ruff)
- build (next build, no tests yet)
- test (pytest, vitest — when added)
- docker compose build
```
