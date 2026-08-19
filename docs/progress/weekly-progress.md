# Weekly Progress — Week of Aug 15, 2026

## Summary

Post–GenAI DLP (M15) polish: Compliance Center UX hierarchy, tenant-configurable IaC and data-movement policies, Reports catalog improvements, shared AI metric insights, Help guide reliability, and Vault enabled by default in Docker Compose.

## Completed

- Compliance Center tabbed hub + framework overview (BL-116)
- IaC evidence tenant config API + modal; Docker `./deploy` mount fix (BL-117)
- OPA data-movement policy tenant config API + modal (BL-118)
- Reports preview modal + catalog activity UX (BL-119)
- AI metric insight hook on Dashboard, Monitoring, Reports, Compatibility (BL-120)
- Help chat layer + guide slug alias fixes (BL-121)
- Vault `VAULT_ENABLED=true` by default in Compose (BL-122)

## Documentation

- [aug-15-compliance-ux-update.md](./aug-15-compliance-ux-update.md) — canonical reference
- Updated: product-roadmap, backlog, genai-dlp-gateway-roadmap, test-plan, milestones, API README, handoffs, vault-deployment

## Metrics

| Milestone | Status |
|-----------|--------|
| M15 GenAI DLP Gateway | Complete (Aug 14) |
| M16 Compliance UX & config | Complete (Aug 15) |

## Next

- Sprint 18 remaining: Bundle MCP scope UI (BL-103)
- Run migrations `059` + `060` on all environments after deploy
