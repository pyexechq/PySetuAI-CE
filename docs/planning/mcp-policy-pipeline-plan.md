# MCP Policy Pipeline — Layer 1 Implementation Plan

> **For agentic workers:** Implement task-by-task; verify in Docker (`make build-backend`, `make migrate`, pytest in backend container).

**Goal:** Enforce policy-bundle MCP scope, tool deny lists, DLP inspect, and audit logging on the live MCP gateway path (chat + multiplex).

**Architecture:** Shared `mcp_access_service.py` filters servers/tools; gateway multiplex and `gateway_service` call it; `select_model` honors key assignments; Alembic adds `policy_bundles.mcp_scope`.

**Tech Stack:** FastAPI, SQLAlchemy async, Alembic, existing `inspect_for_gateway`, `mcp_security_service`, pytest.

## Global Constraints

- No direct FK `client_api_keys` → `mcp_servers`; scope lives on policy bundle.
- Empty/missing `mcp_scope` = all tenant MCP (backward compatible).
- Do not break existing `/v1/mcp` JSON-RPC shape; errors use JSON-RPC error objects for tools/call.
- Client API keys use synthetic deny role `client_key` when no `user.role`.
- Docker: no source bind-mounts — `make build-backend` / `make build-frontend` after code changes.

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/alembic/versions/053_policy_bundle_mcp_scope.py` | Add `mcp_scope` JSONB |
| `backend/app/models/governance.py` | `PolicyBundle.mcp_scope` column |
| `backend/app/schemas/governance.py` | Bundle request/response fields |
| `backend/app/services/mcp_access_service.py` | **New** — filter servers/tools, deny, bundle allowlist |
| `backend/app/services/mcp_audit_service.py` | **New** — write AuditLog for MCP invoke |
| `backend/app/services/llm_router.py` | Filter rules by assigned client keys |
| `backend/app/api/v1/gateway.py` | Multiplex: gate + audit |
| `backend/app/services/gateway_service.py` | Chat path: use shared filter + audit on tool use |
| `backend/app/services/mcp_multiplex_service.py` | Optional: delegate list filtering to access service |
| `backend/tests/test_mcp_access.py` | **New** — unit tests |
| `backend/tests/test_mcp_multiplex_audit.py` | **New** — integration-style tests |
| `backend/tests/test_llm_router_key_binding.py` | **New** — routing key filter |
| `frontend/src/...` bundle editor | MCP scope UI (S18-06) |

---

## S18-01 — Schema: `mcp_scope` on policy bundles

- [ ] Create migration `053_policy_bundle_mcp_scope.py` adding nullable JSONB `mcp_scope` to `policy_bundles`.
- [ ] Add `mcp_scope` to `PolicyBundle` model and Pydantic schemas (`McpScopeConfig` with `mode`, `entries`).
- [ ] Update bundle CRUD in `governance.py` API to accept/return `mcp_scope`.
- [ ] Run `make migrate` and confirm head `053_policy_bundle_mcp_scope`.

**Verify:** API GET bundle returns `mcp_scope: null` for existing rows.

---

## S18-02 — `mcp_access_service` core

- [ ] Create `backend/app/services/mcp_access_service.py` with:
  - `resolve_mcp_scope(bundle)` → mode + entries
  - `filter_servers_for_bundle(servers, bundle)` → filtered server list
  - `filter_tools_for_server(server, tool_names, bundle)` → allowed tool names
  - `resolve_actor_role(ctx)` → `user.role` or `"client_key"`
  - `is_tool_allowed(ctx, db, server, tool_name, deny_rules, bundle)` → bool + reason
- [ ] Wire `is_tool_denied` from `mcp_security_service`.
- [ ] Unit tests in `test_mcp_access.py` for allowlist, deny, compat `all` mode.

**Verify:** `pytest backend/tests/test_mcp_access.py` passes.

---

## S18-03 — Multiplex enforcement + audit

- [ ] In `_handle_mcp_multiplex` (`gateway.py`):
  - Load bundle via `ctx.policy_bundle_id` (reuse `_load_bundle` pattern from gateway_service).
  - Load deny rules via `list_deny_rules` / cache per request.
  - After agent filter, apply `filter_servers_for_bundle`.
  - On `tools/list`: return only allowed tools per server.
  - On `tools/call`: run `is_tool_allowed`; if denied, JSON-RPC error + audit row (status=blocked).
  - Before call: `inspect_for_gateway` on args; block if policy says block.
  - After call: minimal egress inspect on result content (reuse inspect).
  - On success/fail: `mcp_audit_service.log_tool_invoke(...)`.
- [ ] Tests in `test_mcp_multiplex_audit.py` with mocked MCP upstream.

**Verify:** MCP-009 scenario — audit row exists after tools/call; MCP-005 — denied tool returns error.

---

## S18-04 — Chat path alignment

- [ ] In `gateway_service.py` chat flow (~line 512): replace inline server list logic with `mcp_access_service` (keep dynamic tools downstream).
- [ ] If model invokes tools via chat completion tool_calls, audit + inspect on same path where tool execution occurs (if applicable in current code).

**Verify:** Chat with tools uses same bundle filter as multiplex.

---

## S18-05 — Routing rule client key binding

- [ ] In `llm_router.select_model`: for each active rule, if `routing_rule_client_keys` rows exist, rule matches only when `ctx.client_api_key_id` is in assigned set; JWT requests skip key-scoped rules (or only match when no assignments).
- [ ] Add `test_llm_router_key_binding.py`.

**Verify:** Key A assigned to rule R1; Key B does not match R1's condition path.

---

## S18-06 — Bundle MCP scope UI

- [ ] Policy bundle editor: section "MCP tool scope" with mode toggle (`All tenant MCP` / `Allowlist`).
- [ ] Allowlist: multi-select MCP servers from tenant registry; optional per-server tool multiselect from `tool_names`.
- [ ] Save via existing bundle PATCH API.

**Verify:** `make build-frontend`; create bundle with allowlist; key with that bundle sees filtered tools/list.

---

## S18-07 — Docs and backlog closure

- [ ] Update `docs/testing/test-plan.md` MCP-005, MCP-009 to Pass when implemented.
- [ ] Update `docs/testing/release-readiness.md` MCP Governance row.
- [ ] Mark BL-098–BL-103 done in backlog.

**Verify:** Planning docs consistent with code.

---

## Layer 2 preview (Sprint 19)

- BL-104: JWT `purpose`, `lawful_basis` claims; populate `compliance_metadata`.
- BL-105: Dedicated MCP tool response redaction pass.

## Layer 3 preview (Sprint 20+)

- BL-106: Framework rule packs (config-driven, not monolithic OPA).
- BL-107: Retention policies + erasure workflow API.
- BL-108: Optional immutable audit export / WORM store.
