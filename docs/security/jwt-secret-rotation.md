# JWT Secret Rotation — PySetu AI

**Task:** S6-06 / BL-040 · **Addresses:** KI-005

PySetu signs API access tokens with `HS256` and a shared platform secret. Production deployments must not use development defaults.

## How secrets are loaded

On API startup (`backend/app/main.py`):

1. If `VAULT_ENABLED=true` (default in Docker Compose), read `secret/pysetu/platform/jwt_secret` (`value` field).
2. Otherwise use `JWT_SECRET_KEY` from the environment.
3. When `DEBUG=false`, refuse to start if the active secret matches a known insecure default (`vault_service.is_insecure_jwt_secret`).

Check status in the UI: **Settings → Integrations → Secrets Backend (Vault)** shows `JWT from Vault` and `jwt_secret_insecure`.

## Initial setup

### Option A — Environment variable (simplest)

```bash
./scripts/generate-jwt-secret.sh
```

Copy the output into your production secret store:

```env
DEBUG=false
JWT_SECRET_KEY=<generated-64-char-hex>
```

Restart **backend**, **celery-worker**, and **celery-beat** with the same value.

### Option B — Vault-managed (recommended)

1. Configure Vault AppRole (see [vault-deployment.md](./vault-deployment.md)):

   ```bash
   docker compose exec vault sh /scripts/vault-setup-approle.sh
   ```

2. Bootstrap the JWT secret:

   ```bash
   docker compose exec vault sh /scripts/vault-bootstrap-jwt-secret.sh
   ```

3. Set backend environment:

   ```env
   DEBUG=false
   VAULT_ENABLED=true
   VAULT_AUTH_METHOD=approle
   VAULT_ROLE_ID=<from setup script>
   VAULT_SECRET_ID=<from setup script>
   ```

4. Restart API processes. Confirm `jwt_from_vault: true` via `GET /api/v1/security/vault/status` (authenticated) or the Vault status panel in Settings.

## Rotation procedure

Rotating the JWT secret **invalidates all outstanding access tokens**. Plan a maintenance window or accept forced re-login.

### Rotate env-based secret

| Step | Action |
|------|--------|
| 1 | Generate a new secret: `./scripts/generate-jwt-secret.sh` |
| 2 | Update `JWT_SECRET_KEY` in your secret manager / `.env.production` |
| 3 | Rolling restart backend + celery workers with the new value |
| 4 | Verify login and `GET /auth/me` with a fresh token |
| 5 | Revoke/archive the old secret in your secret manager |

### Rotate Vault-managed secret

| Step | Action |
|------|--------|
| 1 | Run `./scripts/vault-bootstrap-jwt-secret.sh` (generates new random secret) or `JWT_SECRET=<new> ./scripts/vault-bootstrap-jwt-secret.sh` |
| 2 | Rolling restart all API processes (they read Vault on startup) |
| 3 | Confirm Settings → Integrations shows secure JWT status |
| 4 | Optional: keep previous KV version in Vault audit log for forensics |

Vault KV v2 retains version history; PySetu always reads the **latest** version.

## Insecure defaults (blocked when DEBUG=false)

| Value | Source |
|-------|--------|
| `change-me-in-production-use-vault` | `config.py` default |
| `dev-secret-change-in-production` | Docker Compose dev |
| `airgap-change-me-before-production` | Air-gap bundle template |
| Empty string | Misconfiguration |

## Production checklist

Use [`.env.production.example`](../../.env.production.example) as the variable reference.

- [ ] `DEBUG=false`
- [ ] Strong `JWT_SECRET_KEY` **or** Vault JWT at `pysetu/platform/jwt_secret`
- [ ] `VAULT_ENABLED=true` (default) with AppRole in production — not dev root token
- [ ] Unique `POSTGRES_PASSWORD` and Redis auth if exposed
- [ ] `OPA_FAIL_OPEN=false` when OPA is required for gateway decisions
- [ ] HTTPS termination at load balancer (`APP_BASE_SCHEME=https`)
- [ ] Rate limiting enabled (`RATE_LIMIT_ENABLED=true`)
- [ ] Demo credentials removed (see S6-08 / Phase 5d)

## Related

- [Vault deployment guide](./vault-deployment.md)
- [Production env template](../../.env.production.example)
- `backend/app/services/vault_service.py`
- `docs/progress/known-issues.md` — KI-005
