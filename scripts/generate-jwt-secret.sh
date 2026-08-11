#!/usr/bin/env sh
# Generate a cryptographically secure JWT signing secret for HelixGuard AI.
# Usage: ./scripts/generate-jwt-secret.sh

set -eu

if command -v openssl >/dev/null 2>&1; then
  SECRET="$(openssl rand -hex 32)"
else
  echo "openssl not found; install OpenSSL or use Python:" >&2
  echo "  python -c \"import secrets; print(secrets.token_hex(32))\"" >&2
  exit 1
fi

cat <<EOF
Generated JWT secret (store securely — do not commit):

JWT_SECRET_KEY=${SECRET}

Next steps:
1. Set JWT_SECRET_KEY in your production environment (.env.production or secret manager).
2. Set DEBUG=false so the API refuses known dev defaults.
3. Restart backend and celery workers together (same secret on all API processes).
4. Optional: store in Vault instead — run ./scripts/vault-bootstrap-jwt-secret.sh

Rotation guide: docs/security/jwt-secret-rotation.md
EOF
