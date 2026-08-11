# Backlog

## P0 — Critical

| ID | Item | Module | Phase |
|----|------|--------|-------|
| BL-001 | Tenant-scoped JWT middleware | Backend | 1 |
| BL-002 | Alembic migrations for Tenant/User | Backend | 1 |
| BL-003 | Login page with auth flow | Frontend | 1 |
| BL-004 | RBAC route guards | Frontend | 1 |

## P1 — High

| ID | Item | Module | Phase |
|----|------|--------|-------|
| BL-012 | MCP server registration API | MCP Governance | 2 |
| BL-013 | OpenAI-compatible gateway proxy | AI Gateway | 2 |
| BL-014 | PII detection pipeline | Data Protection | 2 — Done (S4-28) |

## P2 — Medium

| ID | Item | Module | Phase |
|----|------|--------|-------|
| BL-020 | Audit log ingestion | Audit Explorer | 3 — Done (S4-33) |
| BL-021 | AG Grid audit table | Audit Explorer | 3 — Done (S4-31) |
| BL-037 | External SIEM audit connectors | Audit Explorer | 4 — Done (S4-38) |
| BL-022 | Compliance framework scoring engine | Compliance | 3 — Done (S4-29) |
| BL-023 | Prompt injection detection service | Security | 3 — Done (S4-32) |
| BL-024 | Studio prompt tester | Studio | 4 — Done (S5-02) |
| BL-025 | OpenTelemetry instrumentation | Observability | 3 |
| BL-026 | Policy Studio ↔ Governance Graph linking | Policy Studio | 3 |

## P3 — Low

| ID | Item | Module | Phase |
|----|------|--------|-------|
| BL-030 | Report PDF export (executive/governance templates) | Reports | 4 — Done (S4-02) |
| BL-034 | Scheduled report email delivery to recipients | Reports | 4 — Done (S4-03) |
| BL-035 | Celery report job runner (cron + generating status) | Reports | 4 — Done (S4-03) |
| BL-036 | Executive reporting PDF templates | Reports | 4 — Done (S4-02) |
| BL-031 | Kubernetes Helm chart | DevOps | 5 — Done (S4-35) |
| BL-032 | Air-gap offline bundle | DevOps | 5 — Done (S4-36) |
| BL-033 | Vault integration for secrets | Security | 5 |

## Delivered (reference)

| ID | Item | Sprint / Notes |
|----|------|----------------|
| — | AI Gateway OpenAI/Gemini/Ollama proxy | S3 (supersedes BL-013 scope) |
| — | Reports catalog + CSV export + builder/scheduling UI | S3-01, S3-02, S3-02b |
| — | OpenTelemetry spans + trace IDs in audit | S3-05 / BL-025 |
| — | Policy Studio ↔ Governance Graph linking | S3-06 / BL-026 |
| — | Async report generation + generating status | S4-01 / BL-035 |
| — | Report PDF export + executive PDF templates | S4-02 / BL-030, BL-036 |
| — | Celery scheduler + scheduled email delivery | S4-03 / BL-034, BL-035 |
| — | Policy Studio React Flow canvas | S4-04 / BL-010 |
| — | LLM provider registry CRUD | S4-05 / BL-011 |
| — | MCP server CRUD + connection config | S4-06 / BL-012 |
| — | Policy rule persistence API | S4-07 / BL-010 follow-up |
| — | LLM provider API key in router modal | S4-08 |
| — | MCP live endpoint health checks | S4-09 |
| — | Routing rule target validation | S4-10 |
| — | Routing rule condition evaluator | S4-11 |
| — | MCP live tool discovery (tools/list) | S4-12 |
| — | Weighted LLM routing pool | S4-13 |
| — | Vault-ready secrets abstraction | S4-14 / BL-033 |
| — | Vault in Docker Compose | S4-15 |
| — | Live LLM provider metrics | S4-16 |
| — | MCP session lifecycle (initialize) | S4-17 |
| — | Traffic-based routing rebalance | S4-18 |
| — | MCP session reuse + tools/call | S4-19 |
| — | Vault deployment guide | S4-20 |
| — | MCP tool invoke UI | S4-21 |
| — | Vault AppRole auth | S4-22 / BL-033 |
| — | Scheduled routing rebalance | S4-23 |
| — | Policy bundles + client API keys + gateway binding | S4-25, S4-26 |
| — | Governance Graph per-key bundle visibility | S4-27 |
| — | DLP pipeline + Data Protection API | S4-28 / BL-014 |
| — | GitHub Actions CI (.github/workflows/ci.yml) | S4-37 |
| — | External SIEM connectors (JSON/CEF/NDJSON push + pull export) | S4-38 / BL-037 |
| — | Air-gap Ollama model export/import scripts | S4-39 |
| — | Settings route sub-pages + sidebar submenu | S5-01 |
| — | Studio live security scan + pre-flight prompt lab | S5-02 / BL-024 |
| — | Dashboard 30-day period-over-period KPI trends | S5-05 |
| — | OIDC/SSO discovery design doc | S5-03 |
| — | Slack / ServiceNow alert webhook stubs | S5-04 |
| — | Tenant white-label branding (name/logo/tagline) | S5-06 |
| — | Vault JWT bootstrap + status API | S6-01 / BL-033 |
| — | OIDC provider admin CRUD (Phase 5a) | S6-02 |
| — | OIDC PKCE login + callback JWT issuance | S6-03 |
| — | Backend Ruff lint on full `app/` package in CI | S4-40 |
| — | Air-gap offline bundle (deploy/airgap) | S4-36 / BL-032 |
| — | Kubernetes Helm chart (deploy/helm/helixguard) | S4-35 / BL-031 |
| — | ABAC / OPA gateway policy integration | S4-34 |
| — | Audit log ingestion pipeline + Celery batch ingest | S4-33 / BL-020 |
| — | Prompt injection detection + Security Center API | S4-32 / BL-023 |
| — | Audit Explorer AG Grid + CSV export | S4-31 / BL-021 |
| — | Compliance evidence snapshots + export | S4-30 |
| — | Notification engine (sanitized alerts) | S4 |
| — | Tenant integration settings API | Phase 2 |
| — | Governance graph + observability APIs | Phase 2 |
