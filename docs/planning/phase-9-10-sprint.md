# Phase 9 & 10 Sprint Outline — MCP Platform & Security Parity

**Sprints:** 12–14+ (planned)  
**Status:** **In progress** (Sprint 12)

> Full backlog: [backlog.md](./backlog.md) BL-065–BL-082  
> Matrix: [gateway-parity-roadmap.md](./gateway-parity-roadmap.md)

---

## Phase 9 — MCP Platform & Deep Observability (Sprints 12–13)

### Sprint 12 — MCP platform

| ID | Task | Backlog | Status |
|----|------|---------|--------|
| S12-01 | MCP multiplex gateway URL + routing | BL-065 | Done |
| S12-02 | MCP catalog — curated entries + install flow | BL-066 | Done |
| S12-03 | OAuth auth mediation for MCP credentials | BL-067 | Done |
| S12-04 | Tool risk taxonomy + auto-hide | BL-068 | Done |
| S12-05 | Agent auto-detection + toggles | BL-069 | Done |
| S12-06 | Self-service MCP portal (end-user) | BL-070 | Done |
| S12-07 | Web search MCP + URL filter integrations | BL-071 | |

### Sprint 13 — Observability depth

| ID | Task | Backlog |
|----|------|---------|
| S13-01 | Per-user/team/model cost analytics UI | BL-072 |
| S13-02 | Full request/response log retention | BL-073 |
| S13-03 | OTel trace replay UI | BL-074 |
| S13-04 | Telemetry facade `/telemetry/*` | BL-076 |
| S13-05 | Complete alert webhook wiring (latency, outage) | BL-075 |
| S13-06 | Monitoring live ops panel (requests, tokens, p50, blocks) | BL-076 |

**M10 exit:** MCP catalog install works; cost by user; trace replay; alerts on block.

---

## Phase 10 — Enterprise Security Parity (Sprint 14+)

| ID | Task | Backlog |
|----|------|---------|
| S14-01 | Red team testing suite + export | BL-080 |
| S14-02 | PHI / PCI / financial classifiers | BL-082 |
| S14-03 | Claude.ai compliance API sync | BL-081 |
| S14-04 | Regional routing GA (US/India, Bedrock, Vertex) | BL-077 |
| S14-05 | Gateway SLA operator dashboard | BL-078 |
| S15+ | Endpoint agent (TLS + DLP desktop) — optional | BL-079 |

**M11 exit:** CISO security bundle parity (except optional endpoint agent).

---

## Open decisions (before Sprint 12)

1. MCP catalog — build vs. partner marketplace integration?
2. Web search MCP — first-party vs. integrate existing open MCP?
3. Endpoint agent (BL-079) — in-product or separate SKU?
4. Claude.ai sync (BL-081) — required for first enterprise pilot?
