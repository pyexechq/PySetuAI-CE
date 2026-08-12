# Current Sprint — Sprint 10 Kickoff (Phase 8)

**Updated:** Aug 12, 2026  
**Active focus:** Phase 8 Prompt Lifecycle & Cost Optimization (Prompt store, custom intents, token compression)

> Phase 7 complete: [phase-7-sprint.md](./phase-7-sprint.md)  
> Phase 8 plan: [phase-8-sprint.md](./phase-8-sprint.md)

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

## Sprint 11 Kickoff (Token Saving & Dynamic Tool Calling)

- **S11-01 (BL-063)**: Token saving engine — JSON→TOON / strip markdown (Backend)
- **S11-02 (BL-063, BL-072)**: Token saving dashboard — before/after savings (Frontend)
- **S11-03 (BL-064)**: Dynamic tool calling — rank/filter MCP tools per request (Backend)
- **S11-04 (BL-064)**: Dynamic tool calling UI — MCP Governance config (Frontend)
- **S11-05 (BL-063, BL-064)**: Compounding cost report — routing + tools + compression (Reports)
