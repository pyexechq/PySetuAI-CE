# Compliance UX, Help, Reports & Config — Aug 15, 2026

> **Summary:** Post–GenAI DLP polish: Compliance Center hierarchy, tenant-configurable IaC and data-movement policies, Reports catalog UX, AI metric insights, Help guide fixes, and Vault enabled by default in Docker Compose.

## Compliance Center

| Change | Location |
|--------|----------|
| Tabbed hub: **Frameworks \| Evidence & exports \| Break-glass** (`?tab=`) | `compliance-center-view.tsx` |
| Hero KPIs + quick links (Reports, Data Protection, Audit Explorer, Policy Studio) | Same |
| Framework overview donut + per-framework score bars | `compliance-framework-overview.tsx` |
| Icon-only framework card actions with tooltips | `framework-compliance-card.tsx` |

### Evidence tab panels

| Panel | Configure in UI | API |
|-------|-----------------|-----|
| **GenAI DLP Evidence** | **Data-movement policy** button (not Policy Studio) | `GET/PUT/POST /compliance/data-movement-policy` |
| **Infrastructure evidence** | **Configure** button — scan paths + control checks | `GET/PUT/POST /compliance/iac-evidence/config`, `GET /compliance/iac-evidence/scan` |
| **Break-glass exemptions** | Create/revoke on Exemptions tab | `POST /rag-gateway/exemptions` |

**Policy Studio** remains for **ingress prompt rules** (Block/Redact/Alert). OPA **data-movement** rules for vector hops are configured via **Compliance → GenAI DLP Evidence → Data-movement policy**.

## IaC evidence scanner

| Item | Detail |
|------|--------|
| Deploy root | `IAC_DEPLOY_ROOT` (default `/deploy` in Docker via volume mount `./deploy:/deploy:ro`) |
| Tenant config | `tenant_integrations.iac_scan_paths`, `iac_checks` (migration `059`) |
| Docker fix | Removed invalid `COPY deploy` from `backend/Dockerfile`; manifests mounted at runtime |

## Data-movement policy (tenant)

| Item | Detail |
|------|--------|
| Storage | `tenant_integrations.data_movement_policy` (migration `060`) |
| Fields | `restricted_labels`, `vector_destinations`, `never_exempt_labels` |
| Enforcement | `data_movement_service.py` + OPA `input.tenant_policy` in `gateway.rego` |
| UI | `data-movement-policy-modal.tsx` |

## Reports catalog

| Change | Location |
|--------|----------|
| Preview modal (chart + table) | `report-preview-modal.tsx` |
| Sparklines, icon actions, last-5-generated strip | `report-catalog-table.tsx` |
| Preview API | `POST /reports/{report_id}/preview` |

## AI metric insights

Shared sparkle/insight pattern on metric cards:

| Module | Hook |
|--------|------|
| Executive Dashboard | `use-metric-insight.ts` + `dashboard-metric-insights.ts` |
| Monitoring (overview + security) | Same |
| Reports | Same |
| Compatibility Center | Same |

## Help & guides

| Change | Location |
|--------|----------|
| In-app Help chat + guide articles | `/help`, `help-chat-*` components |
| Slug aliases / fuzzy resolution (fixes 404s) | `help-resources.ts`, `help_context_catalog.py` |
| AI link sanitization | `help_assist_service.py` |
| New articles | `dashboard`, `reports` guides |

## Vault (secrets backend)

| Default | Value |
|---------|-------|
| Docker Compose | `VAULT_ENABLED=true`, `VAULT_TOKEN=dev-root-token` |
| Backend config | `vault_enabled=True` |
| UI | Settings → Integrations → **Secrets & Vault** (default tab) |
| Docs | [vault-deployment.md](../security/vault-deployment.md) |

Air-gap Compose/Helm profiles keep `VAULT_ENABLED=false` (no Vault in offline bundle).

## Backlog IDs (Aug 15)

| ID | Item | Status |
|----|------|--------|
| BL-116 | Compliance Center tabbed UX + framework overview | Done |
| BL-117 | Tenant IaC evidence scanner config UI + API | Done |
| BL-118 | Tenant OPA data-movement policy UI + API | Done |
| BL-119 | Reports catalog preview + activity UX | Done |
| BL-120 | AI metric insights (shared hook) | Done |
| BL-121 | Help guide slug fixes + chat layer | Done |
| BL-122 | Vault enabled by default in Compose | Done |

## Verification

```bash
# Backend (in Docker)
docker exec pysetuai-backend-1 python -m pytest \
  tests/test_iac_evidence_service.py \
  tests/test_data_movement_policy_service.py \
  tests/test_help_assist_service.py -q

# Frontend
cd frontend && npx tsc --noEmit

# Smoke
# Compliance → Evidence → Configure (IaC) + Data-movement policy
# Settings → Integrations → Secrets & Vault → backend: vault
```

## Related docs

- [genai-dlp-gateway-roadmap.md](../planning/genai-dlp-gateway-roadmap.md)
- [vault-deployment.md](../security/vault-deployment.md)
- [product-roadmap.md](../planning/product-roadmap.md) — Phase 15
- [test-plan.md](../testing/test-plan.md) — RAG/COMP/HELP sections
