# SSO / OIDC Integration Design (S5-03)

**Status:** Phase 5a/5b implemented (admin CRUD + PKCE login flow)  
**Target phase:** Phase 5 (enterprise identity)  
**Related backlog:** Future enhancements — SSO/SAML/OIDC enterprise identity integration

## Goals

1. Allow enterprise tenants to sign in with their IdP (Azure AD, Okta, Google Workspace) via OpenID Connect.
2. Preserve HelixGuard multi-tenancy: every authenticated session must resolve to exactly one `tenant_id`.
3. Keep local username/password as a fallback for demo, break-glass, and air-gap deployments.
4. Avoid blocking current JWT-based API clients and gateway client keys.

## Non-goals (Sprint 5)

- Full SAML 2.0 support
- SCIM user provisioning
- Refresh-token rotation service
- Production IdP certificate pinning

## Proposed architecture

```mermaid
sequenceDiagram
    participant Browser
    participant UI as Next.js UI
    participant API as HelixGuard API
    participant IdP as OIDC Provider

    Browser->>UI: Open /login
    UI->>API: GET /auth/oidc/providers?tenant=acme
    API-->>UI: [{slug, display_name, authorization_url}]
    Browser->>IdP: Redirect (PKCE + state + nonce)
    IdP-->>Browser: Authorization code
    Browser->>API: POST /auth/oidc/callback {code, state}
    API->>IdP: Token exchange + JWKS verify
    API->>API: Map claims → User + tenant_id
    API-->>Browser: HelixGuard JWT (same shape as today)
    Browser->>UI: Store token; redirect /dashboard
```

## Identity mapping

| IdP claim | HelixGuard field | Notes |
|-----------|------------------|-------|
| `sub` | `external_subject` (new column on `users`) | Stable IdP subject |
| `email` | `users.email` | Lowercased; required |
| `name` / `given_name` | `users.name` | Optional display name |
| `groups` / `roles` | RBAC role mapping table | Tenant-configured |
| — | `tenant_id` | Resolved before redirect (tenant slug in login URL or email domain) |

### Tenant resolution strategies (pick one per tenant)

1. **Slug in login URL** — `/login?tenant=acme` → OIDC config keyed by tenant slug (recommended for v1).
2. **Email domain** — `acme.com` → tenant mapping table (optional v2).
3. **IdP issuer + client_id** — unique OIDC client per tenant (enterprise tier).

## Data model (planned)

### `tenant_oidc_providers`

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| tenant_id | UUID | FK tenants |
| name | string | Display name ("Okta", "Azure AD") |
| issuer_url | string | OIDC issuer (`/.well-known/openid-configuration`) |
| client_id | string | OAuth client ID |
| client_secret | text | Encrypted via Vault / tenant secrets |
| scopes | string | Default `openid profile email` |
| redirect_uri | string | `{frontend}/auth/oidc/callback` |
| role_claim | string | e.g. `groups` |
| role_mapping | JSONB | `{"Security-Admins": "security_admin"}` |
| enabled | bool | Toggle |
| created_at | timestamptz | |

### `users` extensions

- `auth_provider`: `local` | `oidc` (default `local`)
- `external_subject`: nullable string, unique per `(tenant_id, auth_provider, external_subject)`

## API surface (planned)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/auth/oidc/providers` | List enabled IdPs for tenant (public, tenant slug required) |
| GET | `/auth/oidc/authorize` | Build authorization URL (PKCE verifier stored server-side or in signed cookie) |
| POST | `/auth/oidc/callback` | Exchange code, upsert user, return JWT |
| GET | `/settings/oidc` | Admin: list provider configs |
| POST | `/settings/oidc` | Admin: create provider |
| PUT | `/settings/oidc/{id}` | Admin: update |
| DELETE | `/settings/oidc/{id}` | Admin: remove |

JWT payload remains unchanged: `sub`, `tenant_id`, `role`, `exp`.

## Security controls

- **PKCE (S256)** required for browser flows.
- **State + nonce** stored in Redis with 10-minute TTL.
- **JWKS caching** with kid rotation support (httpx + cachetools).
- **Fail closed** on signature / issuer / audience mismatch.
- **JIT provisioning** optional per tenant (`auto_create_users`, default false for production).
- **Break-glass** local admin always enabled per tenant (config flag).

## RBAC integration

- Default role for JIT users: `developer` or tenant-configured default.
- IdP group → role mapping evaluated after token validation; unknown groups → default role + audit log.
- Platform admins remain local-only in v1.

## UI changes (planned)

1. Login page: "Sign in with SSO" buttons when tenant has OIDC providers.
2. Settings → Organization: OIDC provider CRUD (tenant_admin only).
3. Users table: show `auth_provider` badge (Local / SSO).

## Configuration

```env
OIDC_ENABLED=false
OIDC_CALLBACK_URL=http://localhost:3000/auth/oidc/callback
OIDC_STATE_REDIS_PREFIX=oidc:state:
OIDC_JIT_PROVISION_DEFAULT=false
```

## Migration path

1. **Phase 5a:** Read-only discovery endpoint + admin CRUD (no login).
2. **Phase 5b:** Callback + JWT issuance + JIT off.
3. **Phase 5c:** Group mapping + SCIM (optional).
4. **Phase 5d:** Deprecate shared demo password in production bundles.

## Open questions

1. Single multi-tenant OIDC app vs per-tenant client credentials?
2. Should gateway client keys remain valid when SSO is enforced for UI users?
3. Air-gap mode: disable OIDC entirely or allow on-prem Keycloak only?

## References

- [OpenID Connect Core 1.0](https://openid.net/specs/openid-connect-core-1_0.html)
- [OAuth 2.0 PKCE RFC 7636](https://datatracker.ietf.org/doc/html/rfc7636)
- Existing auth: `backend/app/api/v1/router.py`, `backend/app/core/security.py`
