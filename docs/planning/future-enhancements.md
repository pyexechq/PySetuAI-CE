# Future Enhancements

## AI & ML

- Custom ML models for PII/secret detection
- Adaptive routing based on prompt classification
- Anomaly detection for MCP tool usage patterns
- Federated learning for threat intelligence (privacy-preserving)

## Engineering quality (deferred from Aug 14 audit)

Full triage: [quality-audit-sprint.md](./quality-audit-sprint.md). Sprint 17 covers Dialog, date-range, error UI, and four view states only.

- Nested `api.prompts.list()` client rewrite (keep mixed `api.*` + `*API` until a dedicated API-client sprint)
- Shared FormField / FormSelect library
- Base Recharts wrapper
- Tenant display timezone (store remains UTC)
- Semantic CSS tokens for compliance score colors
- Compliance signal query batching / regional-adapter base class (premature)

## Platform

- Multi-region deployment with data residency controls
- SSO/SAML/OIDC enterprise identity integration
- Custom branding per tenant (white-label)
- Mobile-responsive admin app
- Real-time WebSocket dashboard updates

## Integrations

- ServiceNow incident creation on policy violations
- Slack/Teams alerting for security events
- Scheduled report email delivery (SMTP / SendGrid / SES) — see BL-034
- SIEM export (Splunk, Elastic, Sentinel)
- GitHub/GitLab CI policy gates
- LangChain/LlamaIndex agent SDK plugins

## Advanced Governance

- Approval workflow engine with multi-stage sign-off
- Policy simulation against historical audit data
- Cost allocation by business unit/department
- Model fine-tuning governance and approval
- RAG source governance and access controls

## Deployment

- Helm charts with auto-scaling
- Istio service mesh integration
- Offline/air-gap update bundles
- Disaster recovery runbooks
- SOC2 Type II audit preparation tooling

## HelixGuard-Inspired Enhancements (Aug 13, 2026)

> Identified from HelixGuard AI dashboard review. Full analysis: [helixguard_analysis_and_roadmap.md](../../.gemini/antigravity-ide/brain/24d5e7f0-0378-4184-9303-9163661c333e/helixguard_analysis_and_roadmap.md)

### MCP Registry & Governance

- **REST-to-MCP Auto-Proxy Wizard** (BL-083) — Upload OpenAPI/Swagger, Postman Collection, or GraphQL schema; auto-generate an MCP tool proxy without touching the upstream service
- **SSO Context Credential Injection** (BL-084) — Forward the user's OIDC `access_token` to downstream MCP REST API calls; the LLM prompt never contains real API credentials
- **Tool-Level RBAC Explicit Deny Lists** (BL-085) — Per-group, per-tool deny lists in addition to server-level allowlists (e.g. block `delete_invoice` for Finance Analysts even on an allowed server)
- **Trust Score Fleet Donut Chart** (BL-090) — Fleet-wide trust posture visualization (Low/Medium/High distribution) in MCP Governance Overview
- **MCP Governance Alert Feed** (BL-089) — MCP-scoped alert stream showing high-risk tool calls, unusual access patterns, and server blocks inline in the governance view

### LLM Router

- **Enhanced Visual Routing Engine** (BL-086) — Dynamic SVG fan-out diagram: Routing Engine → animated dashed paths → target model nodes with traffic % and Cloud/Air-Gapped badges; updates live when switching rules
- **Per-Rule Response Format Configuration** (BL-087) — Expose UAG response translation layer as a per-rule dropdown (OpenAI Compatible / Anthropic Native / Vertex Native / Universal Auto-Negotiated)
- **API Key ↔ Routing Rule Explicit Binding** (BL-088) — Show which API keys/service accounts are bound to each routing rule; assign/revoke keys from the Rule Details panel
- **Model Performance Tab in LLM Router** (BL-091) — Latency + throughput charts per model (cloud vs local air-gapped) surfaced within the Router module using existing OTel data
