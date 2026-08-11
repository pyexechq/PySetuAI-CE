# Security Documentation

See also: [Security Architecture](../architecture/security-architecture.md)

## Authentication Flow (Planned)

1. User submits email + password + tenant_slug to `/api/v1/auth/login`
2. Backend validates credentials against tenant-scoped User table
3. JWT issued with `sub`, `tenant_id`, `role`, `exp` claims
4. Frontend stores token in Zustand persist (localStorage)
5. All API requests include `Authorization: Bearer <token>`

## RBAC Matrix

| Permission | platform_admin | tenant_admin | security_admin | compliance_officer | auditor | developer |
|-----------|:-:|:-:|:-:|:-:|:-:|:-:|
| Manage tenants | ✓ | | | | | |
| Manage users | ✓ | ✓ | | | | |
| Manage policies | | ✓ | ✓ | | | |
| View audit logs | ✓ | ✓ | ✓ | ✓ | ✓ | |
| Manage MCP servers | | ✓ | ✓ | | | |
| Use Studio | ✓ | ✓ | ✓ | | | ✓ |
| View compliance | ✓ | ✓ | | ✓ | ✓ | |
| Manage LLM providers | | ✓ | ✓ | | | |

## Secret Management

- Development: `.env` files (gitignored)
- Production: Hashicorp Vault (Phase 5)
- Never commit secrets to version control

## Security Checklist (Pre-Production)

- [ ] Change JWT secret to Vault-managed value
- [ ] Enable TLS/HTTPS
- [ ] Implement rate limiting
- [ ] Enable RBAC on all API routes
- [ ] Add security headers middleware
- [ ] Enable audit logging for auth events
- [ ] Run dependency vulnerability scan
- [ ] Penetration testing
