# Backend Agent Handoff

**Last Updated:** Aug 20, 2026

## Work Completed (Aug 20 — Sprint 24)

- **Policy dry-run against API key bundles** — `POST /policies/test` now accepts `api_key_id`/`bundle_id`, resolves the key → bundle, loads bundle rules, and returns per-rule `rule_results` (`PolicyRuleEvaluationResult`); `GET /policies/rules` accepts `bundle_id`/`default_bundle`
- **Policy engine regex flags** — `content.matches(/pattern/flags)` now honors `i`/`m`/`s`/`x` flags in `_condition_matches` (`policy_engine.py`)
- **Endpoint MCP gateway** — `endpoint-agent/pysetu_agent/mcp_gateway.py` (JSON-RPC framing, `GatewayDecision`, `decide_tool_call`, `McpServerProcess`, `handle_tool_call`, `handle_message`, `run_gateway`, `gateway_config`, `write_gateway_config`); `DiscoveredMcpServer.args` field; daemon CLI flags `--mcp-gateway`, `--server`, `--mcp-gateway-config`; offline dispatch before `missing_fields` check

## Work Completed (Aug 19 — M17)

- Universal AI Gateway (UAG) module with canonical prompt model, protocol translators, model mapping, and translation policies
- Gateway integration: governance runs before translation; response translation and audit trace after upstream call
- REST API: `/api/v1/uag/mappings`, `/policies`, `/stats`, `/simulate`
- Alembic migration `021_uag` for mappings, policies, and translation events
- Dashboard UAG metrics in `build_dashboard_overview()`
- Seed data for acme tenant default mappings and translation policies
- MCP Layer 1 gateway enforcement: policy-bundle MCP scope, tool deny rules,
	ingress/egress inspection, invoke audit, and client-key routing-rule binding
- Endpoint control-plane foundation and Phase 2 local DLP pipeline: endpoint
	registration, policy sync/cache, file scanning, watcher mode, approvals, and
	security-event ingestion
- Fixed endpoint decision vocabulary at the API boundary (`block` → `blocked`,
	`redact` → `redacted`, `allow` → `allowed`)

## Key Files

```text
backend/app/modules/uag/
backend/app/api/v1/uag.py
backend/app/services/uag_admin_service.py
backend/app/models/uag.py
backend/alembic/versions/021_uag.py
backend/tests/test_uag.py
```

## Next Recommended Tasks

1. Complete the pending Policy Studio MCP scope editor (BL-103)
2. Add dedicated MCP tool-result redaction (BL-105)
3. Add native per-OS endpoint adapters for real file/shell enforcement
4. Keep Claude Desktop direct prompt/clipboard interception explicitly out of
	scope until a supported integration boundary is selected
5. MCP gateway: multiplexing (single process, multiple servers) and HTTP/SSE upstream support (currently stdio-only)

