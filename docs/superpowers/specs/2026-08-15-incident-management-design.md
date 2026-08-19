# Incident Management Connectors — Design Spec

**Status:** Approved (Aug 15, 2026)  
**Authors:** Platform / Security  
**Related:** [Implementation Plan](../plans/2026-08-15-incident-management.md) · SF-005 (alert webhook event coverage) · BL-075 (alert webhooks, shipped)

---

## Problem

Security and platform teams need **actionable incidents** in their ITSM / observability tools when PySetu blocks or flags violations — not just in-app notifications or SIEM log streams.

Today:

- **Settings → Integrations → Alert webhooks** supports Slack and ServiceNow with real HTTP POST delivery.
- Gateway blocks (policy, injection, ABAC, egress, rate/token limits) dispatch via `dispatch_tenant_alerts()`.
- MCP tool blocks, RAG/data-movement blocks, security scanner hits, and high-risk audit rows **do not** auto-dispatch.
- No deduplication, ticket ID persistence, or update-on-duplicate behavior.
- No BMC Helix, Datadog, PagerDuty, Jira SM, or generic JSON webhook adapters.

Customers expect parity with enterprise incident workflows: one ticket per meaningful violation cluster, mapped urgency from risk, correlation IDs for Audit Explorer, and tenant-configurable routing.

---

## Goals

1. **Unified security incident events** from all violation sources with a stable schema and fingerprint for dedup.
2. **Hybrid dispatch policy** — auto-ticket only `high` / `critical` risk; dedup by fingerprint within a **15-minute** window; **update** existing external ticket on duplicate (comment/work note), do not create storms.
3. **Incident connectors** (evolution of alert webhooks) for: ServiceNow, BMC Helix ITSM, Datadog, PagerDuty, Jira Service Management, Slack (notify-only), generic JSON webhook.
4. **Audit trail** — `incident.created` / `incident.updated` rows with `external_ticket_id` for Compliance and Audit Explorer.
5. **Settings UI** — configure connectors, dispatch rules, test ping, delivery stats.

## Non-goals (v1)

- Bi-directional ticket sync (close in ITSM → resolve in PySetu) — **P3**.
- Async Celery outbox with retries — **P2** (P1 may dispatch inline with try/except, matching current webhook pattern).
- Replacing SIEM connectors (Splunk/Elastic/Sentinel) — logs stay on SIEM path; incidents stay on connector path.
- PagerDuty on-call scheduling or ServiceNow CMDB enrichment.

---

## Current Architecture

| Layer | Location | Behavior |
|-------|----------|----------|
| Model | `backend/app/models/governance.py` → `AlertWebhook` | `webhook_type`, `endpoint_url`, `auth_token`, `channel`, counters |
| Service | `backend/app/services/alert_webhook_service.py` | `dispatch_tenant_alerts()`, Slack/ServiceNow payloads, `build_gateway_alert_event()` |
| API | `backend/app/api/v1/integrations.py` | CRUD + test at `/settings/alert-webhooks` |
| Schemas | `backend/app/schemas/integrations.py` | Create/update/response DTOs |
| UI | `frontend/src/components/settings/alert-webhooks-panel.tsx` | Slack + ServiceNow only; copy says "stub delivery" (HTTP is real) |
| Gateway dispatch | `backend/app/services/gateway_service.py` | `_dispatch_gateway_block_alert()`, telemetry alerts |
| Rate limits | `backend/app/api/v1/gateway.py` | Direct `dispatch_tenant_alerts` on 429 |

**Not wired:** `prompt_blocked` audit path, `mcp_audit_service`, `rag_gateway` blocks, `security_analytics_service.run_security_scan`, high-risk audit ingestion.

---

## Proposed Architecture

```
Violation sources
  gateway_service, gateway.py (429)
  mcp_audit_service
  rag_gateway / data_movement blocks
  security_analytics_service (scanner)
  audit ingestion (high/critical optional hook)
        │
        ▼
build_security_incident_event(audit_log | inline fields)
        │
        ▼
incident_dispatch_service.evaluate_and_dispatch()
  ├─ tenant IncidentDispatchPolicy (min_risk, sources, dedup_window)
  ├─ fingerprint = hash(source, action, policy_key, actor_bucket)
  ├─ incident_outbox lookup (connector + fingerprint + window)
  └─ adapter registry → HTTP POST / update
        │
        ▼
External ITSM / observability + AuditLog incident.* rows
```

Extend `alert_webhook_service.py` into **`incident_connector_service.py`** (or layer on top without breaking existing API paths). Keep `alert_webhooks` table name for backward compatibility; add columns via migration for connector config JSON and dispatch policy.

---

## Unified Incident Event Model

Canonical dict / Pydantic model `SecurityIncidentEvent`:

| Field | Type | Notes |
|-------|------|-------|
| `event_id` | UUID string | PySetu event id |
| `trace_id` | string \| null | Gateway trace / audit correlation |
| `tenant_id` | UUID | Tenant scope |
| `tenant_slug` | string | Display |
| `source` | enum | `gateway`, `mcp`, `rag`, `scanner`, `audit` |
| `action` | string | e.g. `gateway.policy.block`, `mcp.tool.block`, `rag.movement.block` |
| `title` | string | Human summary |
| `actor` | string | Email or service id |
| `resource` | string | Model, tool, collection, etc. |
| `status` | string | `blocked`, `review`, etc. |
| `risk` | string | `low`, `medium`, `high`, `critical` |
| `policy_bundle` | string \| null | If known |
| `matched_rule` | string \| null | Policy / OPA rule |
| `details` | string | Truncated audit detail |
| `occurred_at` | ISO datetime | Event time |
| `fingerprint` | string | SHA-256 hex of normalized key fields |

**Fingerprint inputs (stable order):** `tenant_id`, `source`, `action`, `policy_bundle or ""`, `matched_rule or ""`, `actor` normalized (email domain bucket optional for dedup breadth).

**Builder:** `build_security_incident_event_from_audit(audit_log: AuditLog)` maps `AuditLog` rows; `build_gateway_alert_event()` remains for gateway-specific titles but should converge to the same shape before dispatch.

---

## Dispatch Policy (tenant defaults)

Stored on tenant or per-connector `config_json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `min_risk` | `high` | Only dispatch when `risk in {high, critical}` |
| `allowed_sources` | all | Subset of `gateway`, `mcp`, `rag`, `scanner`, `audit` |
| `dedup_window_minutes` | `15` | Window for fingerprint match |
| `on_duplicate` | `update` | `update` (comment/work note) or `skip` |
| `enabled` | `true` | Master switch per connector |

Evaluation order:

1. Connector `enabled`?
2. Event `risk` ≥ `min_risk`?
3. Event `source` in `allowed_sources`?
4. Fingerprint match in `incident_outbox` within window?
   - **Yes + on_duplicate=update** → adapter `update_ticket(outbox.external_ticket_id, event)`
   - **Yes + on_duplicate=skip** → return without HTTP
   - **No** → adapter `create_ticket(event)` → insert outbox row

---

## Incident Outbox (dedup + ticket IDs)

New table `incident_outbox`:

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | |
| `connector_id` | UUID FK → `alert_webhooks.id` | |
| `fingerprint` | string(64) | Indexed |
| `external_ticket_id` | string(255) | ITSM incident number / Datadog event id |
| `external_url` | string(1024) nullable | Deep link if returned by API |
| `event_count` | int | Updates in window |
| `first_event_at` | timestamptz | |
| `last_event_at` | timestamptz | |
| `last_event_id` | UUID nullable | Latest PySetu audit id |
| `created_at` | timestamptz | |

Index: `(tenant_id, connector_id, fingerprint, last_event_at)` for window queries.

**P2:** `delivery_status`, `retry_count`, `next_retry_at` for async retries.

---

## Platform Adapters (v1 scope by phase)

### P1 adapters

| Type | API | Create | Update (dedup) |
|------|-----|--------|----------------|
| `servicenow` | Table API `incident` | Existing `build_servicenow_payload` + `correlation_id` | PUT/PATCH work notes |
| `bmc_helix` | REST `HPD:IncidentInterface` | Map urgency/impact from risk | Add work info |
| `webhook` | Customer URL | POST canonical JSON envelope | POST with `action: update` |

### P2 adapters

| Type | API | Notes |
|------|-----|-------|
| `datadog` | Events API v2 | Tags: `pysetu`, tenant, source, risk |
| `pagerduty` | Events API v2 | `routing_key` from config |
| `jira` | REST issue create | Project + issue type + custom fields |
| `slack` | Existing | Notify-only; no ticket id (dedup = fewer messages) |

Adapter interface:

```python
class IncidentAdapter(Protocol):
    async def create_ticket(connector: AlertWebhook, event: SecurityIncidentEvent) -> AdapterResult
    async def update_ticket(connector: AlertWebhook, ticket_id: str, event: SecurityIncidentEvent) -> AdapterResult
```

`AdapterResult`: `external_ticket_id`, `external_url`, `raw_response` (optional, truncated).

### Connector `config_json` examples

```json
// ServiceNow
{
  "assignment_group": "Security Operations",
  "caller_id": "",
  "category": "Security",
  "subcategory": "AI Governance"
}

// BMC Helix
{
  "login_id": "integration_user",
  "company": "Acme",
  "assigned_group": "Security"
}

// PagerDuty (P2)
{
  "routing_key": "Rxxxx"
}

// Jira SM (P2)
{
  "project_key": "SEC",
  "issue_type": "Incident",
  "priority_map": { "critical": "Highest", "high": "High" }
}

// Datadog (P2)
{
  "service": "pysetu-gateway",
  "source_type_name": "pysetu"
}

// Generic webhook
{
  "headers": {},
  "create_path": "",
  "update_path": ""
}
```

---

## Violation Source Wiring

| Source | File | Hook point |
|--------|------|------------|
| Gateway policy/injection/ABAC/egress | `gateway_service.py` | Existing `_dispatch_gateway_block_alert` → migrate to `incident_dispatch_service` |
| Gateway prompt template block | `gateway_service.py` | After audit write (~prompt_blocked) |
| Rate / token budget | `gateway.py` | Existing dispatch → unified service |
| MCP tool block | `mcp_audit_service.py` | After `AuditLog` insert when status=blocked |
| RAG / data movement | `rag_gateway.py` | After `write_rag_audit` when status=blocked |
| Security scanner | `security_analytics_service.py` | After high-risk match in `run_security_scan` |
| High-risk audit | `audit_ingestion_service.py` or post-commit hook | Optional: `risk in (high, critical)` and `status=blocked` |

All hooks call:

```python
await dispatch_security_incident(db, tenant_id, event_or_audit_log)
```

Never raise on delivery failure (log + connector `last_error`, matching current webhook behavior).

---

## API Changes

Extend existing routes (backward compatible):

- `GET/POST/PUT/DELETE /settings/alert-webhooks` — accept new `webhook_type` values and `config_json`, `dispatch_policy` fields.
- `POST /settings/alert-webhooks/{id}/test` — sample `SecurityIncidentEvent`.
- Optional: `GET /settings/incident-outbox` (admin) — recent tickets for debugging (**P2**).

Schemas in `backend/app/schemas/integrations.py`:

- `IncidentDispatchPolicy`
- `ConnectorConfig` (discriminated by `webhook_type`)
- Extend `AlertWebhookResponse` with `config`, `dispatch_policy`, `ticket_count` (aggregate from outbox).

---

## UI (Settings → Integrations)

Evolve **Alert webhooks** panel → **Incident connectors**:

1. Connector type dropdown (all platforms).
2. Endpoint + auth (Bearer, API key header, basic — per type).
3. Type-specific fields (assignment group, routing key, Jira project, etc.).
4. **Dispatch rules** section: min risk, sources checkboxes, dedup window.
5. Test connection button (existing).
6. List: enabled, alerts sent, last error, linked tickets count.
7. Remove "stub delivery" copy; document real HTTP delivery + dedup behavior.

Help text: SIEM export remains under Audit Explorer; incident connectors create **actionable tickets**.

---

## Audit Trail

On successful create/update:

```python
AuditLog(
  action="incident.created" | "incident.updated",
  resource=external_ticket_id,
  status="allowed",
  risk=event.risk,
  details=f"connector={connector.name}; fingerprint={fingerprint}; event_id={event_id}",
  usage_metadata={
    "connector_id": str(connector.id),
    "external_ticket_id": external_ticket_id,
    "external_url": external_url,
    "source": event.source,
    "trace_id": event.trace_id,
  },
)
```

Audit Explorer: optional column/badge "Incident" with external link (**P2** UI).

Compliance remediation: reference incident ticket id in evidence when control tied to blocked event (**P3**).

---

## Security

- Store `auth_token` hashed or encrypted at rest (match existing `AlertWebhook` pattern; consider Vault reference **P2**).
- Never log full tokens or customer webhook payloads at info level.
- Validate `endpoint_url` (HTTPS only in production; allow HTTP localhost in dev).
- Rate-limit test endpoint per tenant.
- Generic webhook: sanitize outbound headers; block internal IP ranges if `DEPLOYMENT_MODE=saas`.

---

## Phased Delivery

### P1 — Core pipeline + three adapters

- `SecurityIncidentEvent` + builders from `AuditLog` and gateway paths
- `incident_dispatch_service` + `incident_outbox` table + migration
- Wire **all** violation sources listed above
- Hybrid dedup (high/critical + 15-min fingerprint + update)
- Adapters: **ServiceNow** (extend), **BMC Helix**, **generic webhook**
- UI: connector types, dispatch rules, updated copy
- Tests: fingerprint, policy evaluation, adapter payload fixtures (HTTP mocked)
- Docs: `docs/api/README.md`, `docs/testing/test-plan.md` section

### P2 — Remaining adapters + reliability

- Datadog, PagerDuty, Jira SM adapters
- Slack as notify-only (no outbox ticket id)
- Optional Celery task `dispatch_incident_async` + retry fields on outbox
- Audit Explorer incident badge + deep link
- `GET /settings/incident-outbox` admin view

### P3 — Lifecycle + compliance

- Bi-directional status sync (webhook inbound or polling)
- Compliance evidence attachment of ticket ids
- Per-policy-bundle connector routing rules
- Metrics dashboard: incidents opened/updated per tenant

---

## Verification (P1)

```bash
cd backend && pytest \
  tests/test_incident_dispatch_service.py \
  tests/test_incident_adapters.py \
  tests/test_alert_webhooks.py \
  tests/test_gateway_egress.py \
  -v
```

Manual:

1. Configure ServiceNow sandbox connector + BMC test endpoint (or webhook.site).
2. Trigger gateway block, MCP block, RAG block, scanner hit.
3. Confirm one ticket per fingerprint cluster; second event within 15 min updates ticket.
4. Confirm `incident.created` / `incident.updated` in Audit Explorer.
5. Settings UI test ping succeeds.

---

## Open Questions (deferred)

- BMC Helix on-prem vs Helix SaaS URL patterns — document per deployment in runbook.
- Datadog: Events vs Incident Management API — P2 spike.
- Actor bucketing for dedup (full email vs domain) — tenant toggle **P2**.

---

## Approval

- **Approved:** Aug 15, 2026 (user confirmation in product review)
- **Next:** [Implementation Plan](../plans/2026-08-15-incident-management.md) — P1 tasks
