#!/usr/bin/env sh
# Configure Vault AppRole for HelixGuard (local dev server).
# Usage: docker compose exec vault sh /scripts/vault-setup-approle.sh
# Or:    VAULT_ADDR=http://localhost:8200 VAULT_TOKEN=dev-root-token ./scripts/vault-setup-approle.sh

set -eu

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-root-token}"
export VAULT_ADDR VAULT_TOKEN

vault secrets enable -path=secret kv-v2 2>/dev/null || true

vault policy write helixguard-secrets - <<'EOF'
path "secret/data/helixguard/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "secret/metadata/helixguard/*" {
  capabilities = ["list", "read", "delete"]
}
EOF

vault auth enable approle 2>/dev/null || true

vault write auth/approle/role/helixguard-api \
  token_policies="helixguard-secrets" \
  token_ttl=1h \
  token_max_ttl=4h \
  secret_id_ttl=0

ROLE_ID="$(vault read -field=role_id auth/approle/role/helixguard-api/role-id)"
SECRET_ID="$(vault write -f -field=secret_id auth/approle/role/helixguard-api/secret-id)"

echo ""
echo "HelixGuard Vault AppRole configured."
echo "Set these in .env.docker (or backend environment):"
echo "VAULT_ENABLED=true"
echo "VAULT_AUTH_METHOD=approle"
echo "VAULT_ROLE_ID=${ROLE_ID}"
echo "VAULT_SECRET_ID=${SECRET_ID}"
echo "VAULT_ADDR=${VAULT_ADDR}"
echo "VAULT_MOUNT_PATH=secret"
echo ""
echo "Remove or leave VAULT_TOKEN empty when using AppRole."
echo ""
echo "Optional platform JWT secret (production):"
echo "  vault kv put secret/helixguard/platform/jwt_secret value=\$(openssl rand -hex 32)"
