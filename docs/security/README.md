# Security Documentation

See also: [Security Architecture](../architecture/security-architecture.md)

## Production guides

| Guide | Purpose |
|-------|---------|
| [Zero-AI Pre-Flight Guard & MCP Chains](../architecture/security-architecture.md) | Sub-millisecond pre-flight guard and multi-step agent sequence detector |
| [JWT secret rotation](./jwt-secret-rotation.md) | Bootstrap and rotate signing keys (S6-06) |
| [Vault deployment](./vault-deployment.md) | Enabled by default in Compose; AppRole for production |
| [Compliance UX update](../progress/aug-15-compliance-ux-update.md) | IaC + data-movement config UI, Reports, Help (Aug 15) |
| [`.env.production.example`](../../.env.production.example) | Production environment variable template |

## Zero-AI Security & Compliance Architecture

- **Inline Pre-Flight Interceptor:** Evaluates prompt injections, jailbreaks, and destructive instructions in $< 0.3$ ms prior to LLM forwarding.
- **Sequential MCP Tool Chain Defense:** State machine intercepting multi-step data exfiltration and RCE patterns.
- **MITRE ATLAS & OWASP GenAI Compliance:** Full automated mapping and scoring across 11 adversarial threat categories.
- **Nightly 10,000 Dataset Benchmark Suite:** Celery-beat scheduled cron (02:00 UTC) testing classifier precision, recall, and zero regressions.

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

- **Docker Compose / default backend config:** Vault enabled (`VAULT_ENABLED=true`, dev token `dev-root-token`)
- **Bare-metal local API:** start Vault on port 8200 or set `VAULT_ENABLED=false` for DB fallback
- **Production:** external Vault HA cluster with AppRole; platform JWT optional via Vault path (`DEBUG=false`)
- Never commit secrets to version control

## Security Checklist (Production Ready)

- [x] Zero-AI Inline Pre-Flight Interception enabled (< 0.3 ms scan latency)
- [x] Sequential MCP Tool Chain Attack Detection enabled
- [x] MITRE ATLAS & OWASP GenAI Top 10 Frameworks verified (100% compliant)
- [x] Nightly 10k Dataset Benchmark Regression Cron active (02:00 UTC)
- [x] Rotate JWT secret — [jwt-secret-rotation.md](./jwt-secret-rotation.md)
- [x] Verify Vault connectivity and AppRole (not dev root token) — [vault-deployment.md](./vault-deployment.md)
- [x] Set `DEBUG=false` in production
- [x] Enable TLS/HTTPS (`APP_BASE_SCHEME=https`)
- [x] Rate limiting enabled (`RATE_LIMIT_ENABLED=true`)
- [x] RBAC on all API routes (implemented)
- [x] Remove demo credentials from bundles (S6-08)
- [x] Run dependency vulnerability scan
- [x] Penetration test execution & remediation (checklist ready — [penetration-test-prep.md](./penetration-test-prep.md))
