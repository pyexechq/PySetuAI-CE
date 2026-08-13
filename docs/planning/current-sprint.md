# Current Sprint — Sprint 15/16 (Phase 11)

**Updated:** Aug 13, 2026  
**Active focus:** M12 HelixGuard Parity complete (BL-083–BL-091). Optional remaining: BL-079 endpoint agent; ops BL-038 / BL-039 / BL-044.

> Phase 8 complete: [phase-8-sprint.md](./phase-8-sprint.md)  
> Phase 9–10 plan: [phase-9-10-sprint.md](./phase-9-10-sprint.md)

## Phase 7 / Sprint 9 Closed (Aug 12 — M8 Milestone Complete)

| ID | Task | Status |
|----|------|--------|
| S9-01 | Routing group entity — name, members, weights | Done |
| S9-02 | Group-as-model — `model: "production"` resolves group | Done |
| S9-03 | Auto-failover — try next provider on 5xx/timeout | Done |
| S9-04 | LLM Router UI — routing groups tab & modal | Done |
| S9-05 | Regional routing spike — Bedrock + Vertex adapters | Done |
| S9-06 | Wire alert webhooks — budget & rate limit breaches | Done |

## Sprint 10 Closed (Aug 12 — Prompt Store & Custom Intents Complete)

- ~~S10-01 Prompt store schema — versions, variables, enforce flag (BL-061)~~ (Done)
- ~~S10-02 Gateway prompt injection — resolve version at ingress (BL-061)~~ (Done)
- ~~S10-03 Prompt store UI — Studio + Settings (BL-061)~~ (Done)
- ~~S10-04 Custom intents MVP — keyword & classification engine (BL-062)~~ (Done)
- ~~S10-05 Custom intents UI — Security / Policy Studio (BL-062)~~ (Done)

## Sprint 11 Closed (Aug 13 — Token Saving & Dynamic Tool Calling Complete)

- ~~**S11-01 (BL-063)**: Token saving engine — JSON→TOON / strip markdown (Backend)~~ (Done)
- ~~**S11-02 (BL-063, BL-072)**: Token saving dashboard — before/after savings (Frontend)~~ (Done)
- ~~**S11-03 (BL-064)**: Dynamic tool calling — rank/filter MCP tools per request (Backend)~~ (Done)
- ~~**S11-04 (BL-064)**: Dynamic tool calling UI — MCP Governance config (Frontend)~~ (Done)
- ~~**S11-05 (BL-063, BL-064)**: Compounding cost report — routing + tools + compression (Reports)~~ (Done)

**M9 — Cost & Prompt Parity:** Prompt store, custom intents, token saving, dynamic tools, compounding cost report.

## Sprint 12 Kickoff (MCP Platform)

- ~~**S12-01 (BL-065)**: MCP multiplex gateway URL + routing~~ (Done)
- ~~**S12-02 (BL-066)**: MCP catalog — curated entries + install flow~~ (Done)
- ~~**S12-03 (BL-067)**: OAuth auth mediation for MCP credentials~~ (Done)
- ~~**S12-04 (BL-068)**: Tool risk taxonomy + auto-hide~~ (Done)
- ~~**S12-05 (BL-069)**: Agent auto-detection + toggles~~ (Done)
- ~~**S12-06 (BL-070)**: Self-service MCP portal (end-user)~~ (Done)
- ~~**S12-07 (BL-071)**: Web search MCP + URL filter integrations~~ (Done)

## Sprint 13 — Observability depth (kickoff)

- ~~**S13-01 (BL-072)**: Per-user/team/model cost analytics UI~~ (Done)
- ~~**S13-02 (BL-073)**: Full request/response log retention~~ (Done)
- ~~**S13-03 (BL-074)**: OTel trace replay UI~~ (Done)
- ~~**S13-04 (BL-076)**: Telemetry facade `/telemetry/*`~~ (Done — summary / operations / security / traces)
- ~~**S13-05 (BL-075)**: Complete alert webhook wiring — latency + upstream outage~~ (Done)
- ~~**S13-06 (BL-076)**: Live monitoring ops panel — requests, tokens, p50, blocks~~ (Done)

**M10 — MCP Platform & Observability:** Complete (S13-01–06, Aug 13).

## Sprint 14 — Enterprise Security Parity (closed Aug 13)

- ~~**S14-01 (BL-080)**: Red-team baseline campaigns with detector-backed scoring and JSON/CSV export~~ (Done Aug 13)
- ~~**S14-02 (BL-082)**: PHI / PCI / financial data classifiers and protected scan API~~ (Done Aug 13)
- ~~**S14-03 (BL-081)**: Claude compliance sync adapter for organizations, users, chats, and DLP evidence~~ (Done Aug 13)
- ~~**S14-04 (BL-077)**: Policy-bundle regional routing for Bedrock and Vertex~~ (Done Aug 13)
- ~~**S14-05 (BL-078)**: Gateway SLA operator dashboard for availability, p99, overhead, provider health, and shared HTTP pool reuse~~ (Done Aug 13)

## Sprint 15/16 — HelixGuard Parity (closed Aug 13)

- ~~**BL-083**: REST-to-MCP auto-proxy wizard~~ (Done)
- ~~**BL-084–BL-091**: LLM Router and MCP UX enhancements~~ (Done)
