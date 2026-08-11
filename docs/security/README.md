# Security Documentation

See also: [Security Architecture](../architecture/security-architecture.md)

## Production guides

| Guide | Purpose |
|-------|---------|
| [JWT secret rotation](./jwt-secret-rotation.md) | Bootstrap and rotate signing keys (S6-06) |
| [Vault deployment](./vault-deployment.md) | AppRole, tenant secrets, JWT in Vault |
| [`.env.production.example`](../../.env.production.example) | Production environment variable template |

## Authentication Flow

1. User submits email + password + tenant_slug to `/api/v1/auth/login` (or SSO via OIDC)
2. Backend validates credentials against tenant-scoped User table
3. JWT issued with `sub`, `tenant_id`, `role`, `exp` claims
4. Frontend stores token in auth cookie / Zustand
5. All API requests include `Authorization: Bearer <token>`

## RBAC Matrix

| Permission | platform_admin | tenant_admin | security_admin | compliance_officer | auditor | developer |
|-----------|:-:|:-:|:-:|:-:|:-:|:-:|
| Manage tenants | ✓ | | | | | |
| Manage users | ✓ | ✓ | | | | |
| Manage policies | | ✓ | ✓ | | | |
| View audit logs | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Manage MCP servers | | ✓ | ✓ | | | |
| Use Governance Sandbox | ✓ | ✓ | ✓ | | | ✓ |
| View compliance | ✓ | ✓ | | ✓ | ✓ | |
| Manage LLM providers | | ✓ | ✓ | | | |

## Secret Management

- Development: `.env` / Docker Compose dev defaults (`DEBUG=true`)
- Production: Vault for tenant keys + optional platform JWT (`DEBUG=false`)
- Never commit secrets to version control

## Security Checklist (Pre-Production)

- [ ] Rotate JWT secret — [jwt-secret-rotation.md](./jwt-secret-rotation.md)
- [ ] Enable Vault (`VAULT_ENABLED=true`) for tenant API keys
- [ ] Set `DEBUG=false` in production
- [ ] Enable TLS/HTTPS (`APP_BASE_SCHEME=https`)
- [ ] Rate limiting enabled (`RATE_LIMIT_ENABLED=true`)
- [ ] RBAC on all API routes (implemented)
- [ ] Remove demo credentials from bundles (S6-08)
- [ ] Run dependency vulnerability scan
- [ ] Penetration testing (S6-09)
