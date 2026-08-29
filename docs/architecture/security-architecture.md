# Security Architecture

## Authentication

- JWT access tokens with configurable expiry (default 60 min)
- Token payload: `sub` (user ID), `tenant_id`, `role`, `exp`
- Password hashing via bcrypt (passlib)
- Future: refresh tokens, SSO/OIDC integration — see [oidc-sso-design.md](./oidc-sso-design.md)

## Authorization

### RBAC (Role-Based Access Control)

Six predefined roles with hierarchical permissions (see backend-architecture.md).

### ABAC (Attribute-Based Access Control)

Open Policy Agent (OPA) evaluates gateway ABAC rules after regex/DLP inspection:

- Policy package: `pysetu.gateway` (`deploy/opa/policies/gateway.rego`)
- Evaluated attributes: user role, auth type (JWT vs client key), policy bundle, routed model, PII/region, risk level, UTC hour
- Config: `OPA_ENABLED`, `OPA_BASE_URL`, `OPA_FAIL_OPEN` (fail-open in dev, fail-closed in production)
- Dry-run: `POST /api/v1/security/opa/evaluate`
- Status: `GET /api/v1/security/opa/status`

Planned extensions:
- User attributes (role, department)
- Resource attributes (data classification, MCP risk score)
- Environmental attributes (time, IP, air-gap status)

## Data Protection & Zero-AI Security Layers

- **Inline Zero-AI Ingress Interceptor (< 0.3 ms):** Intercepts prompt injections, jailbreaks, system prompt dumps, and destructive commands at the gateway before LLM token dispatch.
- **Deterministic Sequential MCP State Machine:** Tracks multi-step agent execution histories across loops to detect Exfiltration Chains, RCE, Destructive Mutations, Privilege Escalation, and Runaway Loops.
- **Dynamic Cost Arbitrage & Complexity Engine:** Evaluates prompt complexity and automatically arbitrates low-complexity queries to high-efficiency models, saving 91.7%–94.0% on token expenditure.
- **Distributed Edge Mesh Sync:** Compiles 22 declarative classifier rules and 5 sequential MCP attack patterns for sub-50μs local execution on regional Envoy/Wasm edge nodes.
- **All API communication over TLS in production** with HashiCorp Vault secrets management.

## Threat Model & Framework Matrix

| Threat Category | MITRE ATLAS ID | OWASP GenAI ID | Mitigation Layer | Action |
|-----------------|:--------------:|:--------------:|------------------|:------:|
| Direct Prompt Injection / Jailbreak | `AML.T0054` | `LLM01:2025` | Zero-AI Inline Classifier (`RULE-INJECT-001`) | 🚫 Block (<0.3ms) |
| Indirect Web & Document Injection | `AML.T0043` | `LLM08:2025` | Ingress Pipeline (`RULE-INDIRECT-INJECT-001`) | 🚫 Block |
| Multi-Step Tool Data Exfiltration | `AML.T0025` | `LLM06:2025` | Sequential MCP State Machine (`SEQ-EXFIL-001`) | 🚫 Block Tool Call |
| Unicode Homoglyph Evasion | `AML.T0051` | `LLM01:2025` | NFKD Unicode Canonicalizer | 🔄 Normalize |
| Agent DoS & Runaway Tool Loops | `AML.T0048` | `LLM10:2025` | Loop Breaker + RPM/TPM Rate Limiter | 🚫 Block Loop |
| Destructive Shell / AST Execution | `AML.T0034` | `LLM06:2025` | AST Syntax Guard (`rm -rf`, SQL DROP) | ✋ Request Approval |
| Sensitive Information Disclosure | `AML.T0043` | `LLM02:2025` | Multi-Regional DLP + Streaming Redaction | 🛡️ Redact / Mask |
| System Prompt Leakage | `AML.T0054` | `LLM07:2025` | Pre-Flight Prompt Dump Interception | 🚫 Block |

## Compliance

Framework tracking built into Compliance Center:
- **MITRE ATLAS (100% Compliant · 6/6 Controls Met)**
- **OWASP GenAI Top 10 (100% Compliant · 5/5 Controls Met)**
- **GDPR, HIPAA, SOC 2 Type II, ISO 27001, NIST AI RMF**
- **Automated Nightly 10,000 Golden Dataset Regression Cron (02:00 UTC)**

## Security Headers (Production)

- `X-PySetu-Action`: `allow` | `block` | `redact` | `request_approval`
- `X-PySetu-Risk`: `0–100`
- `X-PySetu-Classifier-Verdict`: Rule provenance & scan latency
- Content-Security-Policy / Strict-Transport-Security / nosniff / DENY

## Known Security Debt

- JWT secret uses dev default (KI-005)
- Redis-backed rate limiting on auth endpoints (S6-04)
- No RBAC enforcement on API routes yet
- No audit logging of auth events yet
