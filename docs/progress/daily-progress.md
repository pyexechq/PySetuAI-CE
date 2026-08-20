# Daily Progress — Aug 20, 2026

## Completed Today

### Sprint 24 — Endpoint MCP Gateway + Sandbox Policy Dry-Run

- **S24-01–04** Endpoint MCP gateway (`endpoint-agent/pysetu_agent/mcp_gateway.py`) — JSON-RPC framing, `GatewayDecision`, `decide_tool_call`, `McpServerProcess`, `handle_tool_call`, `handle_message`, `run_gateway`, `gateway_config`, `write_gateway_config`; `DiscoveredMcpServer.args` field; daemon CLI flags `--mcp-gateway`, `--server`, `--mcp-gateway-config`; 15 gateway tests + daemon CLI wiring tests
- **S24-05–06** Policy dry-run against API key bundles — `POST /policies/test` accepts `api_key_id`/`bundle_id` and returns per-rule `rule_results`; `GET /policies/rules` accepts `bundle_id`/`default_bundle`
- **S24-07** Governance Sandbox API key selector + real-time evaluation (300 ms debounce) + active-rule highlighting (passed/block/redact/alert) + triggered-rule progress bar
- **S24-08** Policy engine honors regex flags in `content.matches(/.../i)`
- **S24-09** Data Protection Center tabs (DLP scanner, movement policy, exemptions)

### Aug 19 — Unified AI Agent Control Plane (M17)

- **S23-01–09** Advanced Agentic Security — anomaly/exfiltration/injection detectors, Guardian loop, Celery beat schedule
- **S22-01–07** Microsoft Copilot governance
- **S21-01–10** MCP governance depth + endpoint discovery
- **S20-01–10** Endpoint enforcement (detection, policy, scan, approval, shell, clipboard)

## Prior — Aug 13, 2026

## Completed Today

### Phase 9 — MCP Platform & Deep Observability (Sprint 13)

- **S13-01 (BL-072)** Per-user/team/model cost analytics: `usage_metadata` aggregation, `/dashboard/cost-analytics`, dashboard cost card
- **S13-02 (BL-073)** Full request/response log retention: `audit_log_bodies` table, retention settings, purge, request log panel
- **S13-03 (BL-074)** OTel trace replay: `trace_replay_service`, `/observability/traces/{id}`, timeline UI in Monitoring + Audit Explorer
- **S13-04 (BL-076)** Telemetry facade `/telemetry/*`: summary / operations / security / traces — single source for Dashboard + Monitoring
- **S13-05 (BL-075)** Complete alert webhook wiring: latency (`gateway.latency.high`, 30s threshold) + upstream outage (`gateway.upstream.outage`) fired from non-stream + stream paths
- **S13-06 (BL-076)** Live monitoring ops panel: `/telemetry/operations` card in Monitoring Overview — requests, tokens, p50/p95, block rate, recent blocked events

### Sprint 12 recap (Phase 9 MCP platform — closed Aug 13)

- **S12-01–07** MCP multiplex, catalog, OAuth mediation, tool risk taxonomy, agent auto-detection, self-service portal, web search + URL filters — all done

### Phase 10 — Enterprise Security Parity

- **S14-01 (BL-080)** Red-team baseline: six deterministic adversarial/control prompts, detector-backed scoring, authenticated QA run endpoint, and JSON/CSV report export
- **S14-02 (BL-082)** PHI, PCI card, and financial-account classifiers in the DLP redaction pipeline, plus protected `/data-protection/scan` endpoint
- **S14-03 (BL-081)** Claude compliance sync adapter: organization/user/chat ingestion, DLP classification aggregation, tenant-scoped audit evidence, and `/compliance/claude/sync`
- **S14-04 (BL-077)** Regional routing GA: policy-bundle residency maps to provider-native Bedrock and Vertex regions, including US, EU, and India defaults
- **S14-05 (BL-078)** Gateway SLA operator dashboard: availability, error rate, p50/p95/p99 latency, gateway overhead, active providers, and shared HTTP pool reuse instrumentation

### Phase 11 — HelixGuard Parity (Sprint 15/16)

- **BL-083** REST-to-MCP auto-proxy: server-side spec parser (`mcp_spec_proxy_service`) for OpenAPI / Swagger 2.0 / Postman / GraphQL SDL + `POST /mcp/servers/parse-spec`; tool naming matches the client wizard
- **BL-084** SSO context credential injection: tenant-scoped per-server configuration, validated header/claim templates, and `GET/PUT /mcp/servers/{server_id}/sso-injection`
- **BL-085** Tool-level RBAC deny lists: tenant-scoped persistence, role/server/tool matching, case-insensitive enforcement helper, and `GET/POST/DELETE /rbac/tool-deny-lists`

### Migrations

- `047_mcp_url_filters`
- `048_request_log_retention`
- `049_mcp_security_controls`

## Demo Credentials

| Email | Password | Role / Notes |
|-------|----------|--------------|
| admin@acme.com | demo1234 | tenant_admin (tenant: acme) |
| platform@pysetu.com | platform1234 | platform_admin (tenant: platform) |

## Blockers

None

## Next Development Focus

**M8–M12 product feature work is complete (Aug 13).** Remaining optional/ops: BL-079 endpoint agent; BL-038 git push; BL-039 CI pytest; BL-044 strip demo credentials.

See [current-sprint.md](../planning/current-sprint.md) and [gateway-parity-roadmap.md](../planning/gateway-parity-roadmap.md).

## Ops Backlog (non-blocking)

- BL-038 Git remote + push
- BL-039 pytest stabilization in CI
- BL-044 Remove demo credentials from production bundles
