# PySetu AI — Session History & GA Release Reference

**Date**: August 24–25, 2026  
**Scope**: Self-Service Developer Portal, MCP Governance & Live RBAC, Multi-Tenant SaaS Licensing, Marketing & Blog, Multi-Repo Synchronization, and GA Financial & Capacity Models.

---

## 1. Unified Self-Service Developer Portal (`/developer-portal`)

- **Eliminated Redundant Legacy Portals**: Removed mock portal tabs from `/mcp-governance` and consolidated all developer workflows under the dedicated route `/developer-portal`. Added a direct `Developer Portal ↗` header action in MCP Governance and redirected `/mcp-portal` cleanly.
- **Interactive MCP Tool Catalogue**: Built `/developer-portal/catalogue` with granular, per-operation tool selection (`get_contact`, `query_table`, etc.) and shopping-cart request management with required business justifications.
- **Automated Client API Key Provisioning**: Upon request approval, PySetu's backend automatically provisions encrypted, rate-limited client keys with attached OPA and DLP policy bundles. Auto-generates ready-to-use configuration files for **Claude Desktop** (`claude_desktop_config.json`) and **Cursor** (`.cursor/mcp.json`).
- **Interactive Agent Playground**: Built `/developer-portal/playground` allowing developers to test model prompts and tool invocations against live policies with real-time latency and token telemetry.

---

## 2. MCP Governance Access & RBAC Redesign

- **Live Developer Grants Card (`McpDeveloperGrantsCard`)**: Integrated at the top of the **Access & RBAC** tab in `/mcp-governance`. Displays live authorized developers, target MCP servers, granted operation chips, approvers, approval timestamps, and instant **Revoke** capability.
- **Categorized Governance Sub-Sections**:
  - *Identity & Credential Broker*: SSO injection, OAuth broker settings, user authentication mapping.
  - *Agent Policies & Tool Guardrails*: Agent toggles, risk tiers, prompt injection shields, and deny lists.

---

## 3. Multi-Tenant SaaS Entitlements & Tenant Controls

- **SaaS Platform Ops Module Licensing (`/platform`)**: Added `developer_portal` feature entitlement flag to `FEATURE_DEFINITIONS`, `resolve_feature_flags`, and `apply_platform_feature_updates` in `tenant_features_service.py`. Automatically synchronizes `tenant.mcp_portal_enabled`.
- **Tenant Administrator Catalogue Visibility**: Tenant admins can toggle the entire Developer Portal on/off or configure per-server `Published`/`Hidden` catalog visibility (`portal_visible` in `MCPServer.connection_config`).
- **Tenant-Level Disabled Gate**: Added a guard screen in `developer-portal/layout.tsx` that blocks access and renders a clear administrative notice when the portal is disabled for a tenant.

---

## 4. Marketing Homepage, Editions Matrix & Official Blog

- **Marketing Homepage Hero**: Added a dedicated **Self-Service Developer Portal** showcase section in `marketing-home.tsx` featuring the `DeveloperPortalHeroGraphic` interactive mockup.
- **"Choose the Right Edition" Matrix Updated**: Updated `marketing-editions.tsx` across Community (Apache 2.0), Enterprise (Self-Hosted VPC), and PySetu Cloud (SaaS) including Developer Portal, MCP Governance, Copilot Governance, and Agentic Security.
- **Official GA Blog Article**: Authored and seeded `/blog/self-service-developer-portal-mcp-governance` (*"Self-Service Developer Portal: Bridging AI Developers, Governed MCP Tools, and Enterprise RBAC"*).

---

## 5. Multi-Repo Synchronization & Verification

All three target repositories under [`pyexechq`](https://github.com/pyexechq) were synchronized and pushed:
1. **Primary Monorepo (Core / SaaS)**: [`pyexechq/PySetuAI`](https://github.com/pyexechq/PySetuAI) (`main` pushed).
2. **Community Edition (CE)**: [`pyexechq/PySetuAI-CE`](https://github.com/pyexechq/PySetuAI-CE) (`scripts/export-community.sh` executed with Apache 2.0 license).
3. **Enterprise Edition (EE)**: [`pyexechq/PySetuAI-Enterprise`](https://github.com/pyexechq/PySetuAI-Enterprise) (`scripts/build-enterprise-release.sh` executed with Commercial Enterprise license).

### Quality & Test Benchmarks
- **Backend Test Suite**: **471 / 471 passed (100%)** via `anyio` pytest runner in `1.64s`.
- **Frontend Turbopack Build**: **114 / 114 static & dynamic routes compiled** with `0 TypeScript errors`.
- **Containers**: All 8 Docker services healthy.

---

## 6. Financial Forecast & Capacity Models

- **3-Year Revenue Model**:
  - Year 1 (Launch & PMF): **$453k ARR** (EBITDA: -$45k, near break-even)
  - Year 2 (PLG & Expansion): **$2.45M ARR** (EBITDA: +$690k / +28% margin, Net Profit: +$530k)
  - Year 3 (Enterprise Scale): **$8.75M ARR** (EBITDA: +$3.50M / +40% margin, Net Profit: +$2.73M)
- **Throughput & Capacity Benchmarks**:
  - Single Node: **800 – 1,500 RPS** (~350 concurrent streams)
  - Production Cluster (3x nodes): **4,500 – 8,000 RPS** (~2,500 concurrent streams)
  - Enterprise Cluster (Auto-scaled): **25,000+ RPS** (~10,000+ concurrent streams)
  - Gateway Proxy Latency Overhead: **P50: ~8ms**, **P95: ~18ms**, **P99: ~32ms**.
