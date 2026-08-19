# Client API Key Origins & BYOK Ingress — Implementation Plan

> **Design:** [2026-08-15-api-key-origins-and-byok-design.md](../specs/2026-08-15-api-key-origins-and-byok-design.md)  
> **Status:** Not started (Aug 15, 2026)

**Goal:** Per-key API origin overrides and BYOK mirrored ingress keys so customers can migrate with a base-URL change only.

**Suggested backlog IDs:** BL-120 (per-key origins), BL-121 (BYOK ingress)

---

## Phase 1 — Per-key origins (P1, independent)

**Estimate:** 1–2 days

### Backend

- [ ] Migration `061_client_api_key_origins.py` — `client_api_keys.allowed_api_origins JSONB NULL`
- [ ] `resolve_effective_api_origins(key, tenant)` in `client_api_key_service.py`
- [ ] Update `gateway_deps.py` to use effective origins (replace tenant-only check)
- [ ] Extend `backend/app/schemas/access.py` create/update/response
- [ ] Wire `access.py` create/update handlers + origin validation helper
- [ ] `client_key_response()` includes `allowed_api_origins`

### Tests

- [ ] `test_client_api_key_origins.py` — resolution matrix
- [ ] `test_gateway_deps.py` or extend gateway tests — 403/allow per key override

### Frontend

- [ ] `ApiClientApiKey*` types in `frontend/src/lib/api.ts`
- [ ] Origins tri-state in `api-key-limits.tsx` (or sibling `api-key-origins.tsx`)
- [ ] `access-settings.tsx` — show origin mode on key cards; wire create/edit
- [ ] `gateway-settings.tsx` — link to per-key overrides

### Verify

```bash
cd backend && pytest tests/test_client_api_key_origins.py -v
```

---

## Phase 2 — BYOK ingress core (P1)

**Estimate:** 2–3 days  
**Depends on:** Phase 1 optional (origins apply to mirrored keys immediately if Phase 1 done)

### Backend

- [ ] Migration `062_client_api_key_byok.py` — `key_source`, `upstream_pass_through`
- [ ] Refactor `resolve_client_api_key()` — hash lookup without `hg_` prefix requirement
- [ ] `register_mirrored_client_key()` — hash, prefix, duplicate check
- [ ] `get_gateway_context()` — JWT heuristic; client key branch for any resolved hash
- [ ] `GatewayContext` — add `ingress_bearer_token: str | None`, `key_source: str`
- [ ] `POST /client-api-keys/mirrored` (+ optional rotate endpoint)
- [ ] Config flag `byok_ingress_enabled` in `config.py` (default `true` or `false` per product decision)

### Tests

- [ ] `test_mirrored_client_api_key.py` — create, resolve `sk-` token, duplicate rejection
- [ ] `test_gateway_deps.py` — mirrored auth path vs invalid token

### Frontend

- [ ] Create flow: key type selector (PySetu / Mirrored)
- [ ] Mirrored: password input, pass-through toggle, warning copy
- [ ] Badge on key list: `Mirrored`, `Pass-through`

### Verify

```bash
cd backend && pytest tests/test_mirrored_client_api_key.py tests/test_gateway_deps.py -v
```

---

## Phase 3 — Upstream pass-through (P1)

**Estimate:** 1–2 days  
**Depends on:** Phase 2

### Backend

- [ ] Thread `ingress_bearer_token` through `prepare_chat_request` / provider clients
- [ ] OpenAI-compatible client: prefer ingress token when `upstream_pass_through` and `key_source=mirrored`
- [ ] Ensure audit / request logs strip `Authorization`
- [ ] `PUT /client-api-keys/{id}` — allow toggling `upstream_pass_through` (not raw key)

### Tests

- [ ] Mock upstream asserts `Authorization: Bearer sk-test` on pass-through
- [ ] Non-pass-through uses Vault/config key

### Docs

- [ ] Help article in `frontend/src/config/help-resources.ts` — “Migrate from OpenAI with your existing key”
- [ ] `docs/api/README.md` — mirrored key endpoints

### Verify

```bash
cd backend && pytest tests/test_gateway_service.py -k pass_through -v
```

---

## Phase 4 — Hardening & ops (P2)

- [ ] Audit events for mirrored create/rotate/origin change
- [ ] `POST /client-api-keys/{id}/rotate` for both key types
- [ ] Platform/tenant feature flag in admin if required
- [ ] Seed data: optional demo mirrored key (disabled by default)
- [ ] Security review: confirm no plaintext in traces/logs

---

## File touch list

| File | Phase |
|------|-------|
| `backend/app/models/governance.py` | 1, 2 |
| `backend/app/services/client_api_key_service.py` | 1, 2 |
| `backend/app/core/gateway_deps.py` | 1, 2 |
| `backend/app/services/gateway_context.py` | 2, 3 |
| `backend/app/services/gateway_service.py` | 3 |
| `backend/app/api/v1/access.py` | 1, 2 |
| `backend/app/schemas/access.py` | 1, 2 |
| `frontend/src/components/settings/access-settings.tsx` | 1, 2 |
| `frontend/src/components/settings/api-key-limits.tsx` | 1 |
| `frontend/src/lib/api.ts` | 1, 2 |

---

## P1 delivery order

1. **Per-key origins** (Phase 1) — low risk, immediate value for multi-app tenants.
2. **Mirrored key auth** (Phase 2) — unlocks URL-only migration.
3. **Pass-through egress** (Phase 3) — completes “same key end-to-end” story.

Phases 1 and 2 can be parallelized by different owners after migration 061 lands.
