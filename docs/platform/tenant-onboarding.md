# Platform tenant onboarding

Guide for SaaS operators provisioning customer tenants on HelixGuard AI.

## Operator workflow

1. Sign in at `/platform/login` as `platform@helixguard.com` (platform tenant).
2. **New tenant** — set organization name, slug, subdomain, and entry mode.
3. Choose onboarding mode:
   - **Password now** — set an initial admin password (dev/demo only).
   - **Send admin invite link** — generates a secure token; optionally email via SMTP.
4. Customize the invite email under **Customize invite email templates** (3 sample templates included).
5. Preview the rendered email before sending.
6. Share the tenant URL (`https://{subdomain}.localhost:3000` in dev) or invite link.

## Tenant admin workflow

1. Open the invite link (`/accept-invite?token=…`) on the tenant subdomain.
2. Set name and password.
3. Land in the tenant dashboard with full admin access.

## Resend invite

On the tenant list, use **Resend invite** to open the email template modal, preview, and send again.

## Email delivery (dev)

- SMTP defaults to MailHog (`http://localhost:8025`).
- Set `SMTP_ENABLED=true` in `.env.docker` (already default in compose).
- If SMTP is disabled, copy the invite URL from the success card.

## Feature entitlements

Platform operators control module access per tenant (QA, Compatibility Center, Studio, Reports) from the tenant list. Changes apply immediately via `PATCH /platform/tenants/{id}`.

## Operator dashboards

- **Ops** (`/platform/ops`) — fleet SLA, dependency health, block rates, latency.
- **Usage** (same page) — token metering from gateway audit logs (BL-053 foundation).

## API reference

| Endpoint | Purpose |
|----------|---------|
| `POST /platform/tenants` | Provision tenant |
| `POST /platform/tenants/{id}/invites` | Create/resend invite |
| `GET /platform/invite-email/templates` | List email templates |
| `POST /platform/invite-email/preview` | Preview rendered email |
| `POST /auth/accept-invite` | Tenant admin activation |

See [penetration-test-prep.md](../security/penetration-test-prep.md) before production pilots.
