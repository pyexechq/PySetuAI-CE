# Hashicorp Vault Deployment Guide

PySetu AI stores tenant API keys through a secrets abstraction (`secrets_service.py`). **Vault is enabled by default** in Docker Compose and the backend config (`VAULT_ENABLED=true`). Tenant keys are written to Vault KV paths; PostgreSQL columns are cleared on save.

Set `VAULT_ENABLED=false` only for local experiments without a Vault server (keys fall back to the database).

## Local development (Docker Compose)

The stack includes a Vault dev server and enables it for the backend automatically:

| Setting | Default (Compose) |
|---------|-------------------|
| UI / API | http://localhost:8200 |
| Root token | `dev-root-token` |
| KV mount | `secret` (v2, enabled in dev mode) |
| Backend | `VAULT_ENABLED=true`, `VAULT_ADDR=http://vault:8200` |

Override in `.env.docker` if needed:

```env
VAULT_ENABLED=true
VAULT_ADDR=http://vault:8200
VAULT_AUTH_METHOD=token
VAULT_TOKEN=dev-root-token
VAULT_MOUNT_PATH=secret
```

For production-style auth, use AppRole instead of a root token:

```env
VAULT_ENABLED=true
VAULT_AUTH_METHOD=approle
VAULT_ROLE_ID=<role-id>
VAULT_SECRET_ID=<secret-id>
VAULT_ADDR=http://vault:8200
VAULT_MOUNT_PATH=secret
```

Restart the backend after changing these variables. **Settings → Integrations → Secrets & Vault** shows **Secrets backend: vault** and the auth method (`token` or `approle`).

### Secret paths

| Secret | Vault path |
|--------|------------|
| OpenAI API key | `pysetu/tenants/{tenant_id}/integrations/openai_api_key` |
| Gemini API key | `pysetu/tenants/{tenant_id}/integrations/gemini_api_key` |
| Provider API key | `pysetu/tenants/{tenant_id}/providers/{provider_id}/api_key` |

Each secret is stored as KV v2 data: `{ "value": "<key>" }`.

## Production recommendations

1. **Never use dev mode** — deploy Vault in HA mode with auto-unseal (cloud KMS or HSM).
2. **Use AppRole or Kubernetes auth** instead of long-lived root tokens for the PySetu backend.
3. **Scope policies per tenant** — restrict read/write to `pysetu/tenants/{tenant_id}/*` paths.
4. **Enable audit logging** on the Vault cluster and ship logs to your SIEM.
5. **Rotate keys** through Vault versions; PySetu reads the latest version on each gateway request.
6. **Keep Vault enabled** — with `VAULT_ENABLED=true`, plaintext keys are cleared from Postgres on write.

### Example policy (single tenant)

```hcl
path "secret/data/pysetu/tenants/{{tenant_id}}/*" {
  capabilities = ["create", "read", "update", "delete"]
}
```

### Example AppRole setup

Run the helper script against the dev Vault container:

```bash
docker compose exec vault sh -c "VAULT_ADDR=http://127.0.0.1:8200 VAULT_TOKEN=dev-root-token sh /scripts/vault-setup-approle.sh"
```

Or configure manually:

```bash
vault auth enable approle
vault write auth/approle/role/pysetu-api token_policies="pysetu-secrets"
vault read auth/approle/role/pysetu-api/role-id
vault write -f auth/approle/role/pysetu-api/secret-id
```

Configure the backend with `VAULT_AUTH_METHOD=approle`, `VAULT_ROLE_ID`, and `VAULT_SECRET_ID`. The backend caches AppRole tokens and refreshes them before lease expiry.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Vault authentication failed` | Verify token/AppRole credentials and `VAULT_ADDR` reachability from backend container |
| `hvac is not installed` | Rebuild backend image after pulling latest `requirements.txt` |
| Keys still in Postgres | Confirm `VAULT_ENABLED=true` and save keys again from Settings or LLM Router |
| Settings shows `database` backend | Set `VAULT_ENABLED=true` and restart backend — check `.env.docker` or compose environment |
| No Vault in local stack | Run `docker compose up -d vault` or set `VAULT_ENABLED=false` to use DB fallback |

## Related

- BL-033 in `docs/planning/backlog.md`
- [JWT secret rotation](./jwt-secret-rotation.md)
- [Production env template](../../.env.production.example)
- `backend/app/services/secrets_service.py`
- `docs/architecture/security-architecture.md`

### Platform JWT signing key

| Secret | Vault path |
|--------|------------|
| JWT signing key | `pysetu/platform/jwt_secret` |

Bootstrap locally:

```bash
docker compose exec vault sh /scripts/vault-bootstrap-jwt-secret.sh
```

When `VAULT_ENABLED=true` and `DEBUG=false`, the API loads this path on startup instead of `JWT_SECRET_KEY`. See [jwt-secret-rotation.md](./jwt-secret-rotation.md) for rotation runbook.
