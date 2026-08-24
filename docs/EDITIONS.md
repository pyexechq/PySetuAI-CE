# PySetu AI Editions

PySetu AI is distributed across three primary editions, catering to individual developers, self-hosted enterprise deployments, and fully managed SaaS customers.

## Editions Overview

### 1. Community Edition
**Target Audience:** Individual developers, researchers, and small teams.
**Distribution:** Publicly available on GitHub.
**Features:** Includes the core LLM Gateway, basic Agentic MCP auditing, and essential telemetry. It is completely open-source and ready for local development or small-scale internal use.

### 2. Enterprise Edition
**Target Audience:** Large organizations requiring advanced security, compliance, and strict data governance on their own infrastructure.
**Distribution:** Private release provided to enterprise customers for deployment within their own VPC (AWS, GCP, Azure, or on-premise).
**Features:** Includes everything in the Community Edition, plus premium capabilities such as GenAI Data Loss Prevention (DLP), Vault/KMS integration, advanced SOC2/HIPAA compliance reporting, and SAML/OIDC SSO integrations. Note: This version does *not* include PySetu's internal SaaS marketing site or multi-tenant SaaS admin platform.

### 3. SaaS Edition (PySetu Cloud)
**Target Audience:** Customers who want a fully managed, turn-key solution without the overhead of maintaining infrastructure.
**Distribution:** Deployed exclusively on PySetu's production VPS.
**Features:** The complete platform, including everything in the Enterprise Edition, wrapped in a multi-tenant SaaS architecture. This includes the public marketing site and PySetu's internal Tenant Administration Platform (Platform Ops) for managing customer billing, tenant isolation, and global routing.

---

## Feature Matrix

| Feature | Community (GitHub) | Enterprise (Self-Hosted) | SaaS (PySetu Cloud) |
| :--- | :---: | :---: | :---: |
| Core LLM Gateway | ✅ | ✅ | ✅ |
| Agentic MCP Auditing | ✅ | ✅ | ✅ |
| Basic Telemetry & Logs | ✅ | ✅ | ✅ |
| **Self-Service Developer Portal** | ✅ | ✅ | ✅ (Tenant-entitled) |
| **OIDC / SSO (SAML)** | ❌ | ✅ | ✅ |
| **GenAI DLP** | ✅ Basic | ✅ Advanced | ✅ Advanced |
| **Vault/KMS Integration** | ❌ | ✅ | ✅ |
| **Compliance Reports** | ✅ Basic | ✅ Advanced | ✅ Advanced |
| **Marketing Site** | ❌ | ❌ | ✅ |
| **SaaS Tenant Admin** | ❌ | ❌ | ✅ |

## Development Note
The PySetu AI monorepo contains the code for **all three editions**. We use automated CI/CD scripts (`scripts/export-community.sh` and `scripts/build-enterprise-release.sh`) to physically strip out higher-tier proprietary features before releasing code to GitHub or packaging it for Enterprise distribution.
