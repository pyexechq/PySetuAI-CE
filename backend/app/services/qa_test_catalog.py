"""Canonical test case catalog seeded into each QA cycle."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogTestCase:
    case_id: str
    module: str
    title: str
    priority: str
    method: str
    automated_key: str | None = None
    remediation: str | None = None


@dataclass(frozen=True)
class CatalogDefect:
    defect_code: str
    severity: str
    module: str
    title: str
    description: str
    linked_case_id: str | None = None


TEST_CASE_CATALOG: tuple[CatalogTestCase, ...] = (
    # Dashboard
    CatalogTestCase("DASH-001", "Dashboard", "KPI cards render with live API data", "P0", "manual"),
    CatalogTestCase("DASH-002", "Dashboard", "Traffic chart renders time-series", "P1", "manual"),
    CatalogTestCase("DASH-006", "Dashboard", "Cross-tenant KPI isolation", "P0", "integration"),
    # Policy Studio
    CatalogTestCase("POL-001", "Policy Studio", "Create policy", "P0", "manual"),
    CatalogTestCase("POL-005", "Policy Studio", "Policy activation/deactivation", "P0", "manual"),
    CatalogTestCase(
        "POL-010",
        "Policy Studio",
        "Policy evaluation performance",
        "P1",
        "automated",
        "tests/test_policy_engine.py::test_builtin_block_injection",
        "Review policy_engine rules; ensure injection patterns are loaded and evaluate in under SLA.",
    ),
    CatalogTestCase(
        "POL-011",
        "Policy Studio",
        "Region compound PII blocking",
        "P0",
        "automated",
        "tests/test_policy_engine.py::test_region_compound_blocks_when_pii_outside_eu",
    ),
    # LLM Router
    CatalogTestCase("LLM-001", "LLM Router", "Provider CRUD", "P0", "manual"),
    CatalogTestCase("LLM-002", "LLM Router", "Routing rule CRUD", "P0", "manual"),
    CatalogTestCase("LLM-010", "LLM Router", "Correct model selected per rules", "P0", "integration"),
    # MCP Governance
    CatalogTestCase("MCP-001", "MCP Governance", "MCP server registration CRUD", "P0", "manual"),
    CatalogTestCase(
        "MCP-005",
        "MCP Governance",
        "Tool permissions enforcement",
        "P0",
        "integration",
        remediation="Wire policy engine into POST /mcp/servers/{id}/tools/invoke before tool execution. See DEF-001.",
    ),
    CatalogTestCase(
        "MCP-009",
        "MCP Governance",
        "Audit entry on tool invoke",
        "P0",
        "integration",
        remediation="Write AuditLog rows on MCP tool invoke with tenant_id, tool name, and policy outcome. See DEF-002.",
    ),
    # Audit Explorer
    CatalogTestCase("AUD-001", "Audit Explorer", "Request trace visibility", "P0", "manual"),
    CatalogTestCase("AUD-006", "Audit Explorer", "CSV export", "P1", "manual"),
    CatalogTestCase(
        "AUD-007",
        "Audit Explorer",
        "SIEM CEF export format",
        "P1",
        "automated",
        "tests/test_siem_export.py::test_format_cef_contains_action_and_vendor",
    ),
    # Studio
    CatalogTestCase("STU-001", "Studio", "Prompt Lab security pre-scan", "P0", "manual"),
    CatalogTestCase(
        "STU-005",
        "Studio",
        "MCP Simulator live tool invoke",
        "P0",
        "manual",
        remediation="Replace client-side mock in Governance Sandbox MCP tab with POST /mcp/servers/{id}/tools/invoke. See DEF-003.",
    ),
    # Compliance
    CatalogTestCase("COMP-005", "Compliance Center", "Compliance score calculation", "P0", "manual"),
    CatalogTestCase("COMP-006", "Compliance Center", "Snapshot create/export", "P1", "manual"),
    # Security Center
    CatalogTestCase(
        "SEC-001",
        "Security Center",
        "Prompt injection detection",
        "P0",
        "automated",
        "tests/test_security_scan.py::test_security_scan_detects_injection",
    ),
    CatalogTestCase(
        "SEC-004",
        "Security Center",
        "Data exfiltration detection",
        "P0",
        "automated",
        "tests/test_security_scan.py::test_security_scan_detects_exfiltration",
    ),
    CatalogTestCase(
        "SEC-009",
        "Security Center",
        "Rate limiting on auth endpoints",
        "P0",
        "automated",
        "tests/test_rate_limit.py::test_check_rate_limit_blocks_over_limit",
    ),
    # Authentication
    CatalogTestCase("AUTH-001", "Authentication", "Login with valid credentials", "P0", "integration"),
    CatalogTestCase(
        "AUTH-007",
        "Authentication",
        "Rate limiting on login",
        "P0",
        "automated",
        "tests/test_rate_limit.py::test_auth_rate_limit_paths_include_login",
        "Confirm /auth/login is in AUTH_RATE_LIMIT_PATHS and Redis rate limiter is enabled in deployment.",
    ),
    CatalogTestCase(
        "AUTH-008",
        "Authentication",
        "Production JWT secret enforcement",
        "P0",
        "automated",
        "tests/test_vault_oidc.py::test_insecure_jwt_secret_detects_defaults",
    ),
    # Multi-Tenant
    CatalogTestCase(
        "MT-001",
        "Multi-Tenant",
        "Cross-tenant policy access blocked",
        "P0",
        "integration",
        remediation="Add integration tests that attempt cross-tenant reads/writes and assert 403. See DEF-005.",
    ),
    CatalogTestCase(
        "MT-004",
        "Multi-Tenant",
        "JWT tenant_id mismatch rejected",
        "P0",
        "manual",
        remediation="Sign in as tenant A, swap JWT tenant_id claim to tenant B, call any API — expect 403 Tenant mismatch.",
    ),
    # AI Security
    CatalogTestCase(
        "AI-001",
        "AI Security",
        "Prompt injection attack blocked",
        "P0",
        "automated",
        "tests/test_security_scan.py::test_security_scan_detects_injection",
    ),
    CatalogTestCase(
        "AI-004",
        "AI Security",
        "Data exfiltration attack blocked",
        "P0",
        "automated",
        "tests/test_security_scan.py::test_security_scan_detects_exfiltration",
    ),
)

BASELINE_DEFECTS: tuple[CatalogDefect, ...] = (
    CatalogDefect(
        "DEF-001",
        "S1",
        "MCP Governance",
        "No policy enforcement on tool invoke",
        "MCP tool invoke bypasses policy engine — any manage_mcp user can invoke unrestricted tools. "
        "Fix: evaluate active MCP policies in invoke_mcp_tool() before calling upstream.",
        "MCP-005",
    ),
    CatalogDefect(
        "DEF-005",
        "S1",
        "Multi-Tenant",
        "No integration tests for tenant isolation",
        "Application-layer tenant scoping exists but zero integration tests verify cross-tenant access is blocked. "
        "Fix: add pytest integration tests under tests/ that assert 403 on cross-tenant resource access.",
        "MT-001",
    ),
    CatalogDefect(
        "DEF-002",
        "S2",
        "MCP Governance",
        "No audit trail on MCP tool invoke",
        "MCP tool invocations do not create audit log entries.",
        "MCP-009",
    ),
    CatalogDefect(
        "DEF-003",
        "S2",
        "Studio",
        "MCP Simulator uses client-side mock",
        "Studio MCP Simulator simulates responses instead of calling live tools/invoke API. "
        "Fix: call live MCP invoke API from Governance Sandbox simulator component.",
        "STU-005",
    ),
    CatalogDefect(
        "DEF-004",
        "S2",
        "Security Center",
        "Alert webhooks not event-driven",
        "Alert webhooks support CRUD and manual test but do not auto-dispatch on violations. "
        "Fix: dispatch webhooks from policy violation and security scan event handlers.",
    ),
    CatalogDefect(
        "DEF-006",
        "S2",
        "Security",
        "OPA ABAC disabled and fail-open by default",
        "opa_enabled=False and opa_fail_open=True in default configuration.",
    ),
)


def _priority_severity(priority: str) -> str:
    if priority == "P0":
        return "S1"
    if priority == "P1":
        return "S2"
    return "S3"


def build_case_guidance() -> dict[str, dict[str, str | None]]:
    guidance: dict[str, dict[str, str | None]] = {}
    for item in TEST_CASE_CATALOG:
        if not item.remediation:
            continue
        guidance[item.case_id] = {
            "remediation_hint": item.remediation,
            "linked_defect_code": None,
            "suggested_severity": _priority_severity(item.priority),
        }
    for defect in BASELINE_DEFECTS:
        if not defect.linked_case_id:
            continue
        entry = guidance.setdefault(
            defect.linked_case_id,
            {
                "remediation_hint": defect.description,
                "linked_defect_code": defect.defect_code,
                "suggested_severity": defect.severity,
            },
        )
        entry["remediation_hint"] = defect.description
        entry["linked_defect_code"] = defect.defect_code
        entry["suggested_severity"] = defect.severity
    return guidance


CASE_GUIDANCE: dict[str, dict[str, str | None]] = build_case_guidance()
