# Gateway & Platform Parity Roadmap

**Last updated:** Aug 13, 2026  
**Purpose:** Close the gap vs. full-stack AI gateway platforms (OpenRouter Enterprise, Lakera, Prompt Security, QuirlAI-class products) while keeping PySetu’s MCP governance and air-gap differentiators.

**Related:** [product-roadmap.md](./product-roadmap.md) · [backlog.md](./backlog.md) · [phase-7-sprint.md](./phase-7-sprint.md)

---

## Executive summary

PySetu today is strong on **governance, audit, compliance UI, UAG v1, and MCP admin**. It is **not** yet a complete AI gateway product across cost optimization, MCP marketplace, per-user metering, prompt lifecycle, and production alerting.

This plan adds **Phases 7–10** (Sprints 8–14, estimated) to reach **competitive parity** on the capability sets shown in enterprise gateway marketing (7-stage pipeline, dynamic MCP tool calling, MCP platform, cost/routing, observability, CISO security bundle).

---

## Parity matrix (target state)

Legend: **Have** · **Partial** (extend) · **Gap** (net-new)

### 1 — Seven-stage gateway pipeline

| Capability | Today | Target | Backlog |
|------------|-------|--------|---------|
| Identity & Auth (JWT, OIDC/Okta/Google) | Partial | Have | BL-042 ✓, BL-057, BL-058 |
| Per-user / per-team AI usage & attribution | Gap | Have | BL-057, BL-053 |
| Domain allowlists (login / API) | Gap | Have | BL-058 |
| AI traffic rate limits (req/min/hr/day) | Have ✓ | Have | BL-056 ✓ |
| Token budgets (tenant, team, model) | Have ✓ | Have | BL-056 ✓ |
| Security guardrails (PII/PHI/PCI, injection) | Partial | Have | BL-014 ✓, BL-082, BL-023 ✓ |
| Response-path guardrails (ingress + egress) | Have ✓ | Have | BL-059 ✓ |
| Custom intents (trainable classifiers) | Gap | Have | BL-062 |
| Prompt store (versioned, `{{vars}}`, enforce) | Gap | Have | BL-061 |
| Token saving (JSON→TOON / compression) | Partial | Have | BL-063 |
| Weighted routing groups | Partial | Have | BL-050, BL-060 |
| Group name as model parameter | Gap | Have | BL-060 |
| Auto-failover across providers | Gap | Have | BL-060 |
| Regional routing (US/India, Bedrock, Vertex) | Partial | Have | BL-077 |

### 2 — Dynamic tool calling (MCP)

| Capability | Today | Target | Backlog |
|------------|-------|--------|---------|
| Select relevant MCP tools per request (~200 vs 15K tokens) | Have ✓ | Have | BL-064 |
| Automatic tool ranking / filtering | Have ✓ | Have | BL-064 |
| Measurable token reduction KPIs | Partial | Have | BL-064, BL-072 |

### 3 — MCP platform

| Capability | Today | Target | Backlog |
|------------|-------|--------|---------|
| MCP multiplex (single gateway URL) | Have ✓ | Have | BL-065 |
| Curated MCP library + one-click install | Have ✓ | Have | BL-066 |
| Custom MCP via transport URL | Have ✓ | Have | BL-066 |
| OAuth auth mediation for MCP tools | Have ✓ | Have | BL-067 |
| Tool risk taxonomy (read/write/destructive) | Have ✓ | Have | BL-068 |
| Agent auto-detection + per-agent MCP toggles | Have ✓ | Have | BL-069 |
| Self-service MCP / AI portal | Have ✓ | Have | BL-070 |
| Web search MCP + enterprise URL filtering | Gap | Have | BL-071 |

### 4 — Cost & routing

| Capability | Today | Target | Backlog |
|------------|-------|--------|---------|
| Token saving dashboard (before/after) | Partial | Have | BL-063, BL-072 |
| Compounding savings narrative (routing + tools + compression) | Have ✓ | Have | BL-063, BL-064, BL-060 |
| Gateway overhead / SLA operator metrics | Partial | Have | BL-055, BL-078 |
| Connection pooling / latency optimization | Gap | Have | BL-078 |

### 5 — Observability & alerting

| Capability | Today | Target | Backlog |
|------------|-------|--------|---------|
| Per-user / team / model token & cost analytics | Partial | Have | BL-072 |
| Full request logs (prompt, response, tool, guardrail) | Partial | Have | BL-073 |
| Trace replay (OTel-native, stage-by-stage) | Partial | Have | BL-074, BL-025 ✓ |
| Real-time alerts (blocks, budget, latency, outage) | Partial | Have | BL-075 |
| Telemetry facade (`/telemetry/*`) | Gap | Have | BL-076 |
| Live ops dashboard (requests, tokens, p50, blocks) | Partial | Have | BL-076, Monitoring ✓ |

### 6 — CISO / security bundle

| Capability | Today | Target | Backlog |
|------------|-------|--------|---------|
| PII block / redact / monitor | Partial | Have | BL-014 ✓ |
| PHI / PCI / financial classifiers | Gap | Have | BL-082 |
| Prompt injection & jailbreak (every call) | Have | Have | BL-023 ✓ |
| Red team testing (adversarial prompt suite) | Partial | Have | BL-080 |
| Endpoint agent (TLS inspect + DLP desktop) | Gap | Have | BL-079 |
| Claude.ai org compliance API sync | Gap | Have | BL-081 |
| Automatic compliance evidence from pipeline | Partial | Have | BL-052 |

---

## Phased delivery

### Phase 7 — Traffic control & routing parity (Sprints 8–9)

**Goal:** Enterprise-grade limits, metering foundation, routing groups with failover.

| Sprint | Focus | Items |
|--------|-------|-------|
| 8 | Rate limits & budgets | BL-056, BL-057 (usage hooks), BL-058 |
| 9 | Routing groups & failover | BL-060, BL-050 (complete), BL-077 (design + Azure/Bedrock spike) |

**Exit criteria:** Tenant can set req/token budgets; routing group resolves model alias with weighted failover; usage attributed per user/API key.

---

### Phase 8 — Prompt lifecycle & cost optimization (Sprints 10–11)

**Goal:** Prompt store, custom intents, token compression, dynamic MCP tools.

| Sprint | Focus | Items |
|--------|-------|-------|
| 10 | Prompt store + egress guardrails | BL-061, BL-059 |
| 11 | Token saving + dynamic tool calling | BL-063, BL-064, BL-062 (MVP classifier training) |

**Exit criteria:** Prompt versions enforced at gateway; measurable token reduction on MCP and JSON payloads; custom intent rules deployable without code change.

---

### Phase 9 — MCP platform & observability (Sprints 12–13)

**Goal:** MCP marketplace experience, full observability, production alerting.

| Sprint | Focus | Items |
|--------|-------|-------|
| 12 | MCP platform | BL-065, BL-066, BL-067, BL-068, BL-069, BL-070 |
| 13 | Observability depth | BL-072, BL-073, BL-074, BL-075, BL-076 |

**Exit criteria:** Catalog install flow; multiplex URL documented; webhooks fire on guardrail block and budget breach; per-user cost view; trace replay from OTel.

---

### Phase 10 — Enterprise security & polish (Sprint 14+)

**Goal:** CISO bundle, red team, optional endpoint agent, regional GA.

| Sprint | Focus | Items |
|--------|-------|-------|
| 14 | Security bundle + regions | BL-080, BL-082, BL-081, BL-077 GA, BL-078 |
| 15+ | Endpoint agent (optional) | BL-079 — separate product track; air-gap compatible agent |

**Exit criteria:** Red team report export; PHI/PCI policies in Data Protection; regional routing groups in UI; SLA dashboard for operators.

---

## Dependencies

```mermaid
flowchart LR
  BL057[BL-057 Usage metering] --> BL056[BL-056 Rate limits]
  BL057 --> BL072[BL-072 Cost analytics]
  BL050[BL-050 Router CRUD] --> BL060[BL-060 Routing groups]
  BL064[BL-064 Dynamic tools] --> BL065[BL-065 MCP multiplex]
  BL076[BL-076 Telemetry facade] --> BL072
  BL076 --> BL075[BL-075 Alert wiring]
  BL073[BL-073 Full request logs] --> BL074[BL-074 Trace replay]
```

---

## Success metrics (parity KPIs)

| Metric | Target |
|--------|--------|
| MCP tokens per tool call | ≥50% reduction vs. full catalog (dynamic tool calling) |
| JSON payload token savings | ≥30% on eligible structured inputs (token saving) |
| Alert delivery latency | &lt;60s from guardrail block to webhook |
| Per-user cost attribution | 100% of gateway requests tagged user/team/key |
| Routing failover | Automatic switch within 1 failed upstream call |
| Parity backlog completion | BL-056–BL-082 done for M8 |

---

## Milestones

| ID | Name | Target | Backlog range |
|----|------|--------|---------------|
| M8 | Gateway Pipeline Parity | Sprint 9 | BL-056–BL-060, BL-058 |
| M9 | Cost & Prompt Parity | Sprint 11 | BL-061–BL-064, BL-062 |
| M10 | MCP Platform & Observability | Sprint 13 | BL-065–BL-076 |
| M11 | Enterprise Security Parity | Sprint 14+ | BL-077–BL-082, BL-079 optional |

---

## Out of scope (explicit)

- Billing/invoicing integration (BL-053) — metering hooks only until commercial pilot
- SAML 2.0 (BL-047) — unless enterprise deal requires
- 150+ third-party MCP legal/hosting commitments — catalog is curated + partner integrations, not unlimited marketplace day one

---

## Review cadence

- **Monthly:** Parity matrix status (Have / Partial / Gap) updated in this doc
- **Sprint planning:** Pull next phase items from [backlog.md](./backlog.md) P1 parity section
- **QA:** Each BL item requires test catalog entry in [uag-test-plan.md](../testing/uag-test-plan.md) or [test-plan.md](../testing/test-plan.md)
