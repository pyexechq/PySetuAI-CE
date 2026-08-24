# Reports / Dashboard / Policy Engine Sync — Aug 21, 2026

## Context

A sync audit of the reports, dashboard, and policy engine found that the policy engine
was current with all new features, but the **dashboard** and **reports** lagged behind.
This document records the gaps found and the fixes applied to bring all three areas in sync.

## Gaps identified

| # | Area | Gap |
|---|------|-----|
| 1 | Policy engine | `mcp_scope` enforced in backend but had no bundle-editor UI (S18-06) |
| 2 | Reports | "Data Residency" report was a mislabeled audit export, not the real residency computation |
| 3 | Dashboard | Framework rule packs enforced but invisible to compliance scoring |
| 4 | Reports | Executive-summary KPIs/risks were hardcoded, not computed from data |
| 5 | Dashboard | No metrics for agentic security or MCP tool chain events |
| 6 | Reports | No report types for the newest features (agentic security, Copilot, MCP tool chains, framework rule packs) |
| 8 | Policy engine | MCP per-tool policy API existed but had no editing UI |
| 9 | Dashboard | `mcp_violations` counted all MCP traffic, not just blocked (actual violations) |

## Fixes applied

### Gap 2 — Data Residency report uses real residency logic
- `backend/app/services/report_service.py`: added a `data_residency` report source that calls
  `build_data_protection_overview()` and returns per-region records, percentage, status, hubs, and policy.
- Repointed the builtin `data-residency` report from `audit_logs` (action_contains DLP) to the new `data_residency` source.

### Gap 3 — Framework rule packs surfaced in compliance scoring
- `backend/app/services/compliance_service.py`:
  - Added `active_framework_pack_ids: set[str]` to `TenantComplianceSignals`, populated from active bundles' `framework_rule_packs`.
  - Added a rule-pack control to each framework builder (GDPR, HIPAA, SOC 2, ISO/OWASP, NIST) that is `met` when the matching pack is attached to an active bundle.

### Gap 4 — Executive summary computed from data
- `backend/app/api/v1/reports.py`:
  - Computes period-over-period change for total/blocked/allowed/high-risk from the preceding window.
  - Derives `top_risks` from the most common blocked-event details instead of a static list.
  - KPI `change`/`trend` values now reflect real computed deltas.

### Gap 5 — Dashboard metrics for new features
- `backend/app/schemas/auth.py`: added `agentic_security_events`, `mcp_tool_chain_events` and their `_change_pct` fields to `DashboardMetricsResponse`.
- `backend/app/services/dashboard_service.py`: added `_count_agentic_security_events()` (anomalies + exfiltration + injection + guardian) and `_count_mcp_tool_chain_events()`; wired into the metrics response.
- `backend/app/services/dashboard_metric_insights_service.py`: registered the two new metric keys, titles, snapshots, and insight text.
- Frontend: `lib/types/domain.ts`, `lib/api.ts`, `hooks/use-dashboard-overview.ts`, `hooks/use-dashboard-metrics.ts`, `lib/dashboard-metric-insights.ts`, and `components/dashboard/dashboard-content.tsx` — added the two new metric cards ("Agentic Security Events", "MCP Tool Chain Events") and their insight wiring.

### Gap 6 — New report types
- `backend/app/services/report_service.py`: added builtin reports and query templates for
  `agentic_security`, `copilot_governance`, `mcp_tool_chains`, and `framework_rule_packs`, plus the `data_residency` source.

### Gap 8 — MCP per-tool policy editing UI
- `frontend/src/components/mcp-tool-chains/mcp-tool-chains-view.tsx`: added a "Per-Tool Policies" card that lists existing
  per-tool policies and lets admins create (allow/approval/block) and delete them via the existing
  `getMcpToolPolicies` / `upsertMcpToolPolicy` / `deleteMcpToolPolicy` API.

### Gap 9 — MCP violations heuristic fixed
- `backend/app/services/dashboard_service.py`: `mcp_violations` now counts only `status == "blocked"` MCP tool invocations,
  not all MCP traffic. Updated the matching insight text in `dashboard_metric_insights_service.py`.

### Gap 1 — Bundle MCP scope UI (S18-06)
- `frontend/src/lib/api.ts`: added `ApiMcpScopeConfig` / `ApiMcpScopeEntry` types and `mcp_scope` on bundle create/update/response.
- `frontend/src/components/settings/access-settings.tsx`: added an "MCP scope" editor to the new-bundle form
  (mode toggle `all`/`allowlist`/`denylist`, per-server tool multiselect) and an "MCP scope" badge on existing bundles.
- `docs/planning/mcp-policy-pipeline-plan.md`: marked S18-06 done.

## Files changed

Backend:
- `backend/app/services/report_service.py`
- `backend/app/api/v1/reports.py`
- `backend/app/services/compliance_service.py`
- `backend/app/services/compliance_remediation_service.py` (added "Policy Bundles" route for the new rule-pack controls)
- `backend/app/services/dashboard_service.py`
- `backend/app/services/dashboard_metric_insights_service.py`
- `backend/app/schemas/auth.py`

Frontend:
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types/domain.ts`
- `frontend/src/lib/dashboard-metric-insights.ts`
- `frontend/src/hooks/use-dashboard-overview.ts`
- `frontend/src/hooks/use-dashboard-metrics.ts`
- `frontend/src/components/dashboard/dashboard-content.tsx`
- `frontend/src/components/settings/access-settings.tsx`
- `frontend/src/components/mcp-tool-chains/mcp-tool-chains-view.tsx`

Docs:
- `docs/planning/mcp-policy-pipeline-plan.md`
- `docs/progress/reports-dashboard-policy-sync.md` (this file)

## Verification

- Backend: full suite `pytest -q` — **471 passed** (includes compliance, framework rule packs, dashboard, data protection, and MCP tests).
- Frontend: `tsc --noEmit` — clean; `next build` — succeeds (exit 0) after clearing the Turbopack cache.
- Note: `next build` intermittently fails with "Failed to open database" due to a pre-existing Turbopack persistence-cache corruption on this machine; clearing `.next` resolves it and is unrelated to these changes.
