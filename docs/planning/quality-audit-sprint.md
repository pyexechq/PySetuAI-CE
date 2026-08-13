# Quality & Dedup Sprint (Sprint 17 / Phase 12)

**Date:** Aug 14, 2026  
**Status:** Implemented (Sprint 17) — verify with `pytest` + frontend rebuild  
**Source:** Comprehensive system audit (Aug 14) — **verified against the repo, not accepted as-is**  
**Related:** [product-roadmap.md](./product-roadmap.md) · [backlog.md](./backlog.md) · [current-sprint.md](./current-sprint.md)

> **For implementers:** Do not execute the original audit’s 3-week “−2,000 LOC” plan. Several line counts and “missing modules” were wrong. Follow this document.

---

## Audit verdict

The audit is useful as a **theme list** (modals, date-range helpers, error UI, empty/loading states). It is **not** a reliable inventory.

| Claim | Reality |
|-------|---------|
| `audit-log-grid.tsx` is 4,059 lines | **130 lines** (likely token/character count misread as LOC) |
| Dashboard tables 1,618–1,866 lines | **39–44 lines** each |
| ~3,500 lines of modal boilerplate | **7 copies of ~25-line `ModalShell`**. Bodies are domain forms, not duplicates |
| Create `backend/app/core/date_range.py` | **Already exists** (`parse_date_range`, `default_last_n_days`). Three `_resolve_range` wrappers remain |
| 222 TS/TSX files | **~444** under `frontend/src` |
| 30+ backend services | **~82** `backend/app/services/*.py` |
| Type errors in `Downloads/helixguard_ai_dashboard.tsx` | **Not in this repo** — ignore |
| Login has no tenant_slug validation | Pydantic `LoginRequest` exists; slug has default `"acme"` but **no min_length** |
| Compliance API vs service “overlap” | Normal split: routes vs scoring — **not duplication** |
| Feature flags duplicated in `settings.py` | Flags live in `tenant_features_service.py`; router **calls** it — **not duplication** |
| N+1 in `load_tenant_compliance_signals` | **Four independent tables** (policies, audits, MCP, providers), not N+1 of the same relation |
| Regional adapters ~200 LOC to merge | **67 + 77 lines**; shared signatures, different providers — leave until a third adapter |
| ag-Grid vs dashboard tables | **Intentional**: audit explorer is a data grid; dashboard tables are 4-column summaries |
| `api.getX()` vs `promptTemplatesAPI` | Real inconsistency; **do not** rewrite the whole client in this sprint |

**Do not treat as bugs:** UTC timestamps (product is UTC-first), Recharts per-chart tooltips, Badge variants (`default` / `success` / `warning` / `destructive` already exist), “generic `use-api-data` factory”.

---

## Goals (what “done” means)

1. One accessible Dialog primitive; all `ModalShell` copies gone (forms stay in place).
2. Finish **BL-088** client-key assign/unassign (`assign-client-key-modal.tsx` still uncommitted vs `main` HEAD).
3. Single `resolve_range()` in `app.core.date_range`; delete the three copies.
4. App-router `error.tsx` so uncaught UI errors don’t white-screen.
5. Loading / error / empty states on the four highest-traffic views that lack them.
6. Tiny auth schema tightening (`password` / `tenant_slug` min length).

**Out of scope this sprint:** form library, nested `api.prompts.list()` rewrite, chart wrappers, compliance query JOINs, webhook Strategy pattern, tenant timezones, Tailwind “design system” rewrite, mobile redesign of Policy Studio canvas.

---

## Architecture

- **Dialog:** shadcn-style wrapper around `@radix-ui/react-dialog` (already in `package.json`). Shared overlay, focus trap, Escape, `size` (`sm` / `md` / `lg`). Domain modals keep their fields.
- **Date range:** extend existing `backend/app/core/date_range.py` with `resolve_range(from_date, to_date, *, default_days=7) -> tuple[datetime, datetime]`. Callers import it; no local `_resolve_range`.
- **Errors:** Next.js App Router `frontend/src/app/error.tsx` + `global-error.tsx`. No class-component ErrorBoundary unless a client island needs it.
- **Query UX:** reuse TanStack `isLoading` / `isError` already returned by hooks; add view-level placeholders, do not invent a hook factory.

---

## Backlog IDs

| ID | Item | Priority |
|----|------|----------|
| BL-092 | Radix Dialog + replace 7 `ModalShell` copies | P1 |
| BL-093 | BL-088 follow-up: assign/unassign uses routing-rule key APIs | P0 |
| BL-094 | Collapse `_resolve_range` into `app.core.date_range` | P1 |
| BL-095 | App Router error UI (`error.tsx` / `global-error.tsx`) | P1 |
| BL-096 | Loading / error / empty on Audit Explorer, Compliance, Governance Graph, Monitoring | P2 |
| BL-097 | `LoginRequest` min_length on password and tenant_slug | P2 |

Deferred (logged, not scheduled): API client namespace unification; form primitives; chart base; compliance query batching; regional adapter base class; semantic color tokens.

---

## Tasks

### S17-01 (BL-093) — Assign-key modal API — done

`assign-client-key-modal.tsx` calls `assignRoutingRuleClientKey` / `unassignRoutingRuleClientKey` and uses `AppModal`.

### S17-02 (BL-092) — Dialog primitive + ModalShell replacement — done

`frontend/src/components/ui/dialog.tsx` (`AppModal` + Radix primitives). Replaced ModalShell in LLM Router, MCP server, policy create, reports; REST-to-MCP wizard uses `DialogContent`.

### S17-03 (BL-094) — Shared `resolve_range` — done

`app.core.date_range.resolve_range` used by observability, SLA, and telemetry. Tests: `backend/tests/test_date_range.py`.

### S17-04 (BL-095) — Error UI — done

`frontend/src/app/error.tsx` and `global-error.tsx`.

### S17-05 (BL-096) — Query states — done

Audit Explorer loading/error/empty; Compliance error retry; Governance Graph loading; Monitoring overview/traces error.

### S17-06 (BL-097) — Login schema — done

`LoginRequest` `password` and `tenant_slug` `min_length=1`. Tests: `backend/tests/test_login_request.py`.

### S17-07 (BL-092 follow-up) — Remaining overlays — done

Migrated leftover custom overlays onto `AppModal`: login, prompt template/version, policy rule editor, compliance templates, remediation, custom intents, intent tester, platform invite.

---

## Explicitly rejected (from the audit)

| Proposal | Why not now |
|----------|-------------|
| Extract FormField/FormInput/FormSelect | Different validation rules per domain; low reuse vs. churn |
| `use-api-data` factory + query-key helper | Hooks already use TanStack Query; a factory hides tenant/token bugs |
| Nested `api.prompts.list()` rewrite | Large breaking change, no user-facing win |
| Base Recharts wrapper | Charts differ (area vs donut vs bar); shared tooltip only if a third copy appears |
| Force ag-Grid on dashboard | Wrong widget for 5-row KPI tables |
| JOIN all compliance signals | Different tables; 4 round-trips is acceptable |
| Alert webhook Strategy / regional Adapter ABC | Payloads and AWS vs GCP differ; premature abstraction |
| Tenant-local timezone | Product decision; store UTC, display later |
| Hardcoded score colors → CSS vars | Fine as a follow-up polish ticket, not a blocker |
| Downloads/helixguard TS `any` | External file |

---

## Validation

- Frontend: `npm run build` in `frontend/` (or `make build-frontend`)
- Backend: `pytest backend/tests/test_date_range.py` plus SLA/telemetry/auth tests touched
- Manual: Dialog keyboard (Tab, Escape), assign-key bind, date-range on Observability/Monitoring/SLA

---

## Effort

About **3–5 days**, not 3 weeks. Expected net LOC change: **small** (shared Dialog + `resolve_range`; not −2,000).
