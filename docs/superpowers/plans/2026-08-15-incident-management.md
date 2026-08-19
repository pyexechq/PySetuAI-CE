# Incident Management Connectors — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Design:** [2026-08-15-incident-management-design.md](../specs/2026-08-15-incident-management-design.md)  
**Status:** Not started (Aug 15, 2026)  
**Suggested backlog IDs:** BL-122 (incident connectors P1)

**Goal:** Auto-create and deduplicated-update external ITSM tickets for all PySetu security violations via incident connectors (ServiceNow, BMC Helix, generic webhook in P1).

**Architecture:** Normalize violations to `SecurityIncidentEvent`, evaluate tenant hybrid dispatch policy (high/critical + 15-min fingerprint dedup), persist ticket IDs in `incident_outbox`, deliver via adapter registry layered on existing `alert_webhooks` table and integrations API.

**Tech stack:** Python 3.12, FastAPI, SQLAlchemy async, Alembic, httpx, React/Next.js settings UI, pytest + httpx mock.

## Global Constraints

- **Min risk for auto-ticket:** `high` and `critical` only (tenant-configurable later; default from spec).
- **Dedup window:** `15` minutes; **on_duplicate:** `update` (work note / comment), not new ticket.
- **Delivery:** Never raise from dispatch path; log failures on connector `last_error` (match `alert_webhook_service.py`).
- **Backward compatibility:** Keep `/settings/alert-webhooks` routes and `alert_webhooks` table name; extend columns/types.
- **P1 adapters only:** `servicenow`, `bmc_helix`, `webhook` — not Datadog/PagerDuty/Jira until P2.
- **HTTPS:** Production connector URLs must use `https://` (config flag may allow `http://localhost` in dev).
- **No Celery in P1:** Inline async dispatch with try/except.

---

## File map (P1)

| Responsibility | Create | Modify |
|----------------|--------|--------|
| Event model + fingerprint | `backend/app/schemas/incident.py` | — |
| Outbox model | `backend/app/models/governance.py` | Alembic `061_incident_outbox.py` |
| Dispatch + dedup | `backend/app/services/incident_dispatch_service.py` | — |
| Adapters | `backend/app/services/incident_adapters/` (`base.py`, `servicenow.py`, `bmc_helix.py`, `webhook.py`) | `alert_webhook_service.py` (delegate or thin re-export) |
| API schemas | `backend/app/schemas/integrations.py` | `backend/app/api/v1/integrations.py` |
| Violation hooks | — | `gateway_service.py`, `gateway.py`, `mcp_audit_service.py`, `rag_gateway.py`, `security_analytics_service.py` |
| UI | — | `alert-webhooks-panel.tsx`, `api.ts` |
| Tests | `test_incident_dispatch_service.py`, `test_incident_adapters.py`, `test_incident_hooks.py` | `test_alert_webhooks.py` |

---

## Phase 1 — Schema & migration

**Estimate:** 0.5 day

### Task 1: SecurityIncidentEvent + dispatch policy schemas

**Files:**
- Create: `backend/app/schemas/incident.py`
- Modify: `backend/app/schemas/integrations.py`

**Interfaces:**
- Produces: `SecurityIncidentEvent` (Pydantic), `IncidentDispatchPolicy`, `IncidentFingerprint.compute(event) -> str`

- [ ] **Step 1: Write failing test for fingerprint stability**

```python
# tests/test_incident_dispatch_service.py
from app.schemas.incident import SecurityIncidentEvent, compute_incident_fingerprint

def test_fingerprint_stable_for_same_inputs():
    e1 = SecurityIncidentEvent(
        event_id="a", tenant_id="t1", tenant_slug="acme",
        source="gateway", action="gateway.policy.block",
        title="Blocked", actor="user@acme.com", resource="gpt-4",
        status="blocked", risk="high", details="x",
        occurred_at="2026-08-15T00:00:00Z",
        policy_bundle="standard", matched_rule="pii",
    )
    e2 = e1.model_copy()
    assert compute_incident_fingerprint(e1) == compute_incident_fingerprint(e2)
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `cd backend && pytest tests/test_incident_dispatch_service.py::test_fingerprint_stable_for_same_inputs -v`

- [ ] **Step 3: Implement `incident.py` schemas + fingerprint**

- [ ] **Step 4: Extend `integrations.py` with optional `config_json`, `dispatch_policy` on create/update/response**

- [ ] **Step 5: Run test — expect PASS**

- [ ] **Step 6: Commit** `feat: add security incident event schemas`

### Task 2: Database migration — outbox + connector columns

**Files:**
- Create: `backend/alembic/versions/061_incident_outbox.py`
- Modify: `backend/app/models/governance.py`

**Interfaces:**
- Produces: `IncidentOutbox` model; `AlertWebhook.config_json`, `AlertWebhook.dispatch_policy_json` (JSONB nullable)

- [ ] **Step 1: Add `IncidentOutbox` model with indexes**

- [ ] **Step 2: Alembic revision `061` — table `incident_outbox` + alter `alert_webhooks` add JSONB columns**

- [ ] **Step 3: Run migration locally** `alembic upgrade head`

- [ ] **Step 4: Commit** `feat: add incident outbox and connector config columns`

---

## Phase 2 — Event builders

**Estimate:** 0.5 day

### Task 3: Build events from AuditLog and gateway

**Files:**
- Create: `backend/app/services/incident_event_builder.py`
- Modify: `backend/app/services/alert_webhook_service.py` (optional: call builder from `build_gateway_alert_event`)

**Interfaces:**
- Produces: `build_security_incident_event_from_audit(audit_log: AuditLog) -> SecurityIncidentEvent`
- Produces: `map_audit_source(audit_log) -> str` (`gateway`|`mcp`|`rag`|`scanner`|`audit`)

- [ ] **Step 1: Failing test** — gateway blocked audit row → `source=gateway`, `risk=high`

- [ ] **Step 2: Implement builder** using `AuditLog.action`, `status`, `risk`, `actor`, `resource`, `details`, `usage_metadata`

- [ ] **Step 3: Test PASS + commit** `feat: build security incident events from audit logs`

---

## Phase 3 — Dispatch service + dedup

**Estimate:** 1 day

### Task 4: incident_dispatch_service

**Files:**
- Create: `backend/app/services/incident_dispatch_service.py`

**Interfaces:**
- Consumes: `SecurityIncidentEvent`, `IncidentDispatchPolicy`, `IncidentOutbox`, adapters
- Produces: `async def dispatch_security_incident(db, tenant_id, event: SecurityIncidentEvent | AuditLog) -> list[DispatchResult]`
- Produces: `def should_dispatch(event, policy) -> bool`
- Produces: `async def find_outbox_match(db, tenant_id, connector_id, fingerprint, window_minutes) -> IncidentOutbox | None`

- [ ] **Step 1: Test** — high risk dispatches; medium skipped

- [ ] **Step 2: Test** — duplicate fingerprint within 15 min calls update path (mock adapter)

- [ ] **Step 3: Test** — duplicate after window creates new outbox row

- [ ] **Step 4: Implement evaluate + outbox CRUD + audit log `incident.created` / `incident.updated`**

- [ ] **Step 5: Commit** `feat: incident dispatch with hybrid dedup`

---

## Phase 4 — Adapters (P1)

**Estimate:** 1.5 days

### Task 5: Adapter registry

**Files:**
- Create: `backend/app/services/incident_adapters/base.py`
- Create: `backend/app/services/incident_adapters/servicenow.py`
- Create: `backend/app/services/incident_adapters/bmc_helix.py`
- Create: `backend/app/services/incident_adapters/webhook.py`
- Create: `backend/app/services/incident_adapters/__init__.py` — `get_adapter(webhook_type)`

**Interfaces:**
- Produces: `AdapterResult(external_ticket_id, external_url)`
- Consumes: `SecurityIncidentEvent`, `AlertWebhook`, `config_json`

- [ ] **Step 1: Test ServiceNow payload** includes `correlation_id` = `trace_id` or `event_id`

- [ ] **Step 2: Migrate `build_servicenow_payload` logic into adapter; add update work-note method**

- [ ] **Step 3: Test BMC Helix payload** urgency/impact mapping from risk

- [ ] **Step 4: Implement BMC adapter** (POST JSON; parse incident number from response)

- [ ] **Step 5: Test generic webhook** POST envelope `{ "action": "create"|"update", "event": {...} }`

- [ ] **Step 6: Wire `VALID_WEBHOOK_TYPES`** → `servicenow`, `bmc_helix`, `webhook`, `slack` (slack notify-only, no update in P1)

- [ ] **Step 7: Commit** `feat: incident adapters for ServiceNow BMC and webhook`

### Task 6: Integrations API

**Files:**
- Modify: `backend/app/api/v1/integrations.py`
- Modify: `backend/app/services/alert_webhook_service.py` — `create_webhook` validates new types + JSON

- [ ] **Step 1: Accept `config_json`, `dispatch_policy` on create/update**

- [ ] **Step 2: Test endpoint creates `bmc_helix` connector**

- [ ] **Step 3: Commit** `feat: extend alert webhook API for incident connectors`

---

## Phase 5 — Wire violation sources

**Estimate:** 1 day

### Task 7: Gateway + MCP + RAG + scanner hooks

**Files:**
- Modify: `backend/app/services/gateway_service.py`
- Modify: `backend/app/api/v1/gateway.py`
- Modify: `backend/app/services/mcp_audit_service.py`
- Modify: `backend/app/api/v1/rag_gateway.py`
- Modify: `backend/app/services/security_analytics_service.py`

**Interfaces:**
- Consumes: `dispatch_security_incident(db, tenant_id, audit_log_or_event)`

- [ ] **Step 1: Replace `_dispatch_gateway_block_alert` internals with `dispatch_security_incident` (keep function name or deprecate)**

- [ ] **Step 2: Add dispatch after `prompt_blocked` audit write in `gateway_service.py`**

- [ ] **Step 3: After MCP `AuditLog` insert when `status=="blocked"` → dispatch**

- [ ] **Step 4: After RAG `write_rag_audit` when blocked → dispatch**

- [ ] **Step 5: After `run_security_scan` high/critical findings → dispatch (or batch one event per scan)**

- [ ] **Step 6: Integration test** `tests/test_incident_hooks.py` with mocked HTTP

- [ ] **Step 7: Commit** `feat: wire security incident dispatch to all violation sources`

---

## Phase 6 — Frontend

**Estimate:** 1 day

### Task 8: Settings UI

**Files:**
- Modify: `frontend/src/components/settings/alert-webhooks-panel.tsx`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Extend `ApiAlertWebhook*` types with `config_json`, `dispatch_policy`**

- [ ] **Step 2: Connector type options: ServiceNow, BMC Helix, Generic webhook, Slack**

- [ ] **Step 3: Type-specific config fields (assignment group, BMC company, webhook headers)**

- [ ] **Step 4: Dispatch rules UI: min risk select, source checkboxes, dedup window**

- [ ] **Step 5: Update description — remove "stub delivery"; explain dedup**

- [ ] **Step 6: Manual test in dev UI**

- [ ] **Step 7: Commit** `feat: incident connector settings UI`

---

## Phase 7 — Docs & verification

**Estimate:** 0.25 day

- [ ] Update `docs/api/README.md` — incident connector types, dispatch policy, outbox behavior
- [ ] Update `docs/testing/test-plan.md` — incident connector manual test checklist
- [ ] Update `docs/testing/security-findings.md` — close SF-005 partial gap note when hooks ship
- [ ] Run full P1 pytest suite:

```bash
cd backend && pytest \
  tests/test_incident_dispatch_service.py \
  tests/test_incident_adapters.py \
  tests/test_incident_hooks.py \
  tests/test_alert_webhooks.py \
  -v
```

- [ ] Commit `docs: incident management connectors P1`

---

## P2 preview (do not implement in P1)

- Adapters: `datadog`, `pagerduty`, `jira`
- Celery `dispatch_incident_async` + outbox retries
- Audit Explorer incident badge + external URL
- `GET /settings/incident-outbox`

## P3 preview

- Bi-directional ticket status sync
- Compliance evidence links to `external_ticket_id`

---

## Self-review (spec coverage)

| Spec requirement | Plan task |
|------------------|-----------|
| Unified event model | Task 1, 3 |
| All violation sources | Task 7 |
| Hybrid dedup 15 min | Task 4 |
| ServiceNow extend | Task 5 |
| BMC Helix | Task 5 |
| Generic webhook | Task 5 |
| incident_outbox | Task 2, 4 |
| Audit trail incident.* | Task 4 |
| Settings UI | Task 8 |
| Datadog/PagerDuty/Jira | P2 preview only |

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-15-incident-management.md`.

**Recommended next step:** Implement **Phase 1 (Task 1–2)** in an isolated branch — schemas + migration — then Phase 3 dispatch service before adapters, so hooks can be tested with a mock adapter early.

**Execution options:**

1. **Subagent-driven (recommended)** — one subagent per task, review between tasks  
2. **Inline execution** — use superpowers:executing-plans with checkpoints after Phase 3 and Phase 5
