#!/usr/bin/env sh
# Write or rotate the platform JWT secret in Hashicorp Vault (KV v2).
# Usage:
#   VAULT_ADDR=http://localhost:8200 VAULT_TOKEN=dev-root-token ./scripts/vault-bootstrap-jwt-secret.sh
#   JWT_SECRET=<existing> ./scripts/vault-bootstrap-jwt-secret.sh   # rotate to a known value
#
# Vault path: secret/pysetu/platform/jwt_secret  (field: value)

set -eu

VAULT_ADDR="${VAULT_ADDR:-http://127.0.0.1:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-root-token}"
VAULT_MOUNT="${VAULT_MOUNT_PATH:-secret}"
JWT_PATH="${VAULT_MOUNT}/pysetu/platform/jwt_secret"
export VAULT_ADDR VAULT_TOKEN

if ! command -v vault >/dev/null 2>&1; then
  echo "vault CLI not found. Install Hashicorp Vault CLI or run via container:" >&2
  echo "  docker compose exec vault sh /scripts/vault-bootstrap-jwt-secret.sh" >&2
  exit 1
fi

vault secrets enable -path="${VAULT_MOUNT}" kv-v2 2>/dev/null || true

if [ -n "${JWT_SECRET:-}" ]; then
  NEW_SECRET="${JWT_SECRET}"
elif command -v openssl >/dev/null 2>&1; then
  NEW_SECRET="$(openssl rand -hex 32)"
else
  echo "Set JWT_SECRET or install openssl to auto-generate." >&2
  exit 1
fi

vault kv put "${JWT_PATH}" value="${NEW_SECRET}"

cat <<EOF

JWT secret stored at: ${JWT_PATH}

Backend configuration:
  VAULT_ENABLED=true
  VAULT_ADDR=${VAULT_ADDR}
  DEBUG=false

On startup the API loads this value from Vault (see backend/app/main.py).
Restart all backend and celery processes after rotation.

Existing sessions signed with the old secret will be invalidated.

Full rotation runbook: docs/security/jwt-secret-rotation.md
EOF
