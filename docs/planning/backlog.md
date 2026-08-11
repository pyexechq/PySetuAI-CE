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
| BL-033 | Vault integration for secrets | Security | 5 — Done (S6-01) |

## P4 — Ops & Release (backlog)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-038 | Configure Git remote and push `main` | DevOps | — | Repo is local-only today |
| BL-039 | Run and stabilize full backend pytest suite (local + CI) | QA | — | Tests exist; prod Docker image has no pytest |
| BL-040 | Production env template — rotate JWT secret, enforce Vault | Security | 5 — Done (S6-06) |
| BL-041 | OIDC JIT provisioning toggle in Settings UI | Settings / Identity | 5c — Done (S6-05) |
| BL-042 | OIDC IdP group → HelixGuard role mapping | Identity | 5c — Done (S6-07) |
| BL-043 | SCIM user provisioning (optional) | Identity | 5c | Out of scope for Sprint 6 |
| BL-044 | Remove demo credentials from production bundles | Security | 5d | Phase 5d in OIDC design |
| BL-045 | Penetration test prep checklist + remediation backlog | Security | 5 | Pre-M5 gate |
| BL-046 | Update stale progress docs and roadmap milestones | Docs | — | `daily-progress.md`, roadmap checkboxes |
| BL-047 | SAML 2.0 support | Identity | 6+ | Deferred from Phase 5 |
| BL-048 | Istio service mesh integration | DevOps | 6+ | Deferred from Phase 5 |

## Phase 6 — Enterprise Operations

| ID | Item | Module | Phase | Status |
|----|------|--------|-------|--------|
| BL-050 | LLM Router dynamic rule CRUD backend | LLM Router | 6 | Done |
| BL-051 | MCP live trust/risk scoring backend | MCP Governance | 6 | Done |
| BL-052 | Compliance framework live scoring engine | Compliance | 6 | Done |
| BL-053 | Platform billing / usage metering hooks | Platform | 6 | Done (audit `usage_metadata`; billing UI deferred) |
| BL-054 | Tenant self-service onboarding workflow | Platform | 6 | Done |
| BL-055 | SLA / uptime dashboards for operators | Observability | 6 | Done |

## Phase 7 — Gateway Pipeline Parity (planned)

> Full matrix: [gateway-parity-roadmap.md](./gateway-parity-roadmap.md)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-056 | AI traffic rate limits + token budgets (tenant/team/model) | Gateway | 7 | Req/min/hr/day; Redis counters |
| BL-057 | Per-user / per-team usage metering & attribution | Platform / Gateway | 7 | API key + OIDC subject tagging |
| BL-058 | Domain allowlists (login + API client origins) | Identity | 7 | Tenant policy in Settings |
| BL-059 | Response-path guardrails (egress scan parity) | Gateway / Security | 7 | Extend UAG response flow |
| BL-060 | Routing groups — alias-as-model, weighted failover | LLM Router | 7 | Depends BL-050 |
| BL-077 | Regional routing (US/India, Bedrock, Vertex, vLLM) | LLM Router / UAG | 7–10 | Spike in Sprint 9; GA Sprint 14 |

## Phase 8 — Prompt Lifecycle & Cost Optimization (planned)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-061 | Prompt store — versions, templates, enforce mode | Gateway / Studio | 8 | Central prompt registry |
| BL-062 | Custom intents — trainable content classifiers | Security / Policy | 8 | MVP: rule + embedding hybrid |
| BL-063 | Token saving — JSON→TOON / payload compression | Gateway | 8 | Opt-in per route; preserve responses |
| BL-064 | Dynamic tool calling — relevant MCP tools only | MCP Governance | 8 | Tool ranking + token KPI |

## Phase 9 — MCP Platform & Deep Observability (planned)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-065 | MCP multiplex — single gateway URL | MCP Governance | 9 | Zero agent config change story |
| BL-066 | MCP catalog — curated library + one-click install | MCP Governance | 9 | Custom MCP via transport URL |
| BL-067 | MCP OAuth auth mediation / token broker | MCP Governance | 9 | Vault-backed credential broker |
| BL-068 | Tool risk taxonomy (read/write/destructive) | MCP Governance | 9 | Auto-hide disabled tools |
| BL-069 | Agent auto-detection + per-agent MCP toggles | MCP Governance | 9 | Claude/OpenAI/Gemini agents |
| BL-070 | Self-service MCP / AI portal | MCP Governance | 9 | End-user browse + connect |
| BL-071 | Web search MCP + enterprise URL filtering | MCP Governance | 9 | Zscaler/FortiGate/Cisco hooks |
| BL-072 | Per-user/team/model token & cost analytics | Observability | 9 | Depends BL-057 |
| BL-073 | Full request/response log store | Audit Explorer | 9 | Retention + search + export |
| BL-074 | OTel-native trace replay | Observability | 9 | Stage-by-stage debug UI |
| BL-075 | Wire alert webhooks to gateway events | Security | 6–9 | Fixes DEF-004; blocks/budget/latency |
| BL-076 | Telemetry facade API (`/telemetry/*`) | Backend | 9 | Dashboard/Monitoring single source |

## Phase 10 — Enterprise Security Parity (planned)

| ID | Item | Module | Phase | Notes |
|----|------|--------|-------|-------|
| BL-078 | Gateway SLA metrics — p99 overhead, uptime, pooling | Observability | 10 | Operator-facing |
| BL-079 | Endpoint agent — TLS inspect + DLP (macOS/Windows) | Security | 10+ | Optional separate deliverable |
| BL-080 | Red team testing suite | Security / QA | 10 | Adversarial campaigns + reports |
| BL-081 | Claude.ai compliance API sync | Compliance | 10 | Orgs, users, chats, DLP |
| BL-082 | PHI / PCI / financial classifiers | Data Protection | 10 | Extend BL-014 |

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
| — | Auth rate limiting on login/token endpoints | S6-04 |
| — | Platform tenant management portal (SaaS) | Post-S6 |
| — | Product marketing site + tenant subdomain entry modes | Post-S6 |
| — | Public legal pages (terms, privacy, cookies, trust) | Post-S6 |
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
| — | Universal AI Gateway v1 + Compatibility Center | Aug 2026 / M7 |
| — | Monitoring hub + UI overlap consolidation | Aug 2026 |
| — | Compliance remediation API + dedicated compliance fetch | Aug 2026 |
