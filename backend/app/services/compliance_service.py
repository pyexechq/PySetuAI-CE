"""Compliance framework scoring and per-control evaluation for the Compliance Center."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog, LLMProvider, MCPServer, Policy
from app.schemas.dashboard import DashboardComplianceControl, DashboardComplianceFramework

ControlStatus = str  # met | not_met | in_progress


@dataclass(frozen=True)
class TenantComplianceSignals:
    active_policy_names: set[str]
    draft_policy_count: int
    audit_log_count: int
    pii_events: int
    blocked_requests: int
    total_requests: int
    mcp_server_count: int
    high_risk_mcp_count: int
    llm_provider_count: int
    compliance_score: float
    block_rate: float


async def load_tenant_compliance_signals(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    compliance_score: float,
    block_rate: float,
    pii_events: int,
    blocked_requests: int,
    total_requests: int,
    audit_start,
    audit_end,
) -> TenantComplianceSignals:
    policy_rows = await db.execute(
        select(Policy.name, Policy.status).where(Policy.tenant_id == tenant_id, Policy.policy_type == "policy")
    )
    policies = policy_rows.all()
    active_policy_names = {name for name, status in policies if status == "active"}
    draft_policy_count = sum(1 for _, status in policies if status == "draft")

    audit_count_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.timestamp >= audit_start,
            AuditLog.timestamp < audit_end,
        )
    )
    audit_log_count = audit_count_result.scalar() or 0

    mcp_rows = await db.execute(select(MCPServer.risk_score).where(MCPServer.tenant_id == tenant_id))
    mcp_scores = [row[0] for row in mcp_rows.all()]
    high_risk_mcp_count = sum(1 for score in mcp_scores if score >= 40)

    provider_count_result = await db.execute(
        select(func.count(LLMProvider.id)).where(
            LLMProvider.tenant_id == tenant_id,
            LLMProvider.is_active.is_(True),
        )
    )
    llm_provider_count = provider_count_result.scalar() or 0

    return TenantComplianceSignals(
        active_policy_names=active_policy_names,
        draft_policy_count=draft_policy_count,
        audit_log_count=audit_log_count,
        pii_events=pii_events,
        blocked_requests=blocked_requests,
        total_requests=total_requests,
        mcp_server_count=len(mcp_scores),
        high_risk_mcp_count=high_risk_mcp_count,
        llm_provider_count=llm_provider_count,
        compliance_score=compliance_score,
        block_rate=block_rate,
    )


def _control(
    *,
    id: str,
    title: str,
    requirement: str,
    status: ControlStatus,
    evidence: str | None = None,
    remediation: str | None = None,
    pysetu_module: str | None = None,
) -> DashboardComplianceControl:
    return DashboardComplianceControl(
        id=id,
        title=title,
        requirement=requirement,
        status=status,
        evidence=evidence,
        remediation=remediation,
        pysetu_module=pysetu_module,
    )


def _framework_status(score: float, passed: int, controls: int) -> str:
    ratio = passed / controls if controls else 0
    if score >= 90 and ratio >= 0.95:
        return "compliant"
    if score >= 70 and ratio >= 0.6:
        return "partial"
    return "at-risk"


def _build_gdpr_controls(signals: TenantComplianceSignals) -> list[DashboardComplianceControl]:
    has_eu_pii = "PII Redaction — EU" in signals.active_policy_names
    has_us_pii = "PII Redaction — US" in signals.active_policy_names
    has_dlp = "DLP Classification" in signals.active_policy_names or signals.draft_policy_count > 0

    return [
        _control(
            id="gdpr-art25",
            title="Art. 25 — Data protection by design",
            requirement="Embed privacy controls in AI gateway and policy enforcement before data reaches models.",
            status="met" if has_eu_pii and has_us_pii else "in_progress" if has_eu_pii or has_us_pii else "not_met",
            evidence="Active PII redaction policies at the gateway." if has_eu_pii or has_us_pii else None,
            remediation="Activate PII Redaction — EU and US policies in Policy Studio.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="gdpr-art30",
            title="Art. 30 — Records of processing",
            requirement="Maintain auditable records of AI requests, policy actions, and data classifications.",
            status="met" if signals.audit_log_count >= 10 else "in_progress" if signals.audit_log_count else "not_met",
            evidence=f"{signals.audit_log_count} audit events captured in the last 30 days."
            if signals.audit_log_count
            else None,
            remediation="Enable gateway traffic and route requests through PySetu to populate Audit Explorer.",
            pysetu_module="Audit Explorer",
        ),
        _control(
            id="gdpr-art32",
            title="Art. 32 — Security of processing",
            requirement="Apply technical measures (encryption, access control, prompt/output inspection).",
            status="met" if "Jailbreak Prevention" in signals.active_policy_names else "in_progress",
            evidence="Security control policies active at the AI gateway."
            if "Jailbreak Prevention" in signals.active_policy_names
            else None,
            remediation="Enable Jailbreak Prevention and Prompt Injection Guard policies.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="gdpr-art17",
            title="Art. 17 — Right to erasure workflow",
            requirement="Document and execute erasure requests for personal data used in AI workflows.",
            status="not_met",
            remediation="Define an erasure runbook and link retention policies to audit log purge schedules.",
            pysetu_module="Settings",
        ),
        _control(
            id="gdpr-art33",
            title="Art. 33 — Breach notification readiness",
            requirement="Detect incidents within 72 hours and maintain an escalation path.",
            status="in_progress" if signals.blocked_requests else "not_met",
            evidence=f"{signals.blocked_requests} blocked events available for incident review."
            if signals.blocked_requests
            else None,
            remediation="Configure alert routing in Observability and document breach notification owners.",
            pysetu_module="Observability",
        ),
        _control(
            id="gdpr-art35",
            title="Art. 35 — DPIA for high-risk AI",
            requirement="Complete a Data Protection Impact Assessment for high-risk LLM use cases.",
            status="in_progress" if has_dlp else "not_met",
            evidence="DLP classification policy drafted." if signals.draft_policy_count else None,
            remediation="Finalize DLP Classification policy and attach DPIA evidence in Reports.",
            pysetu_module="Reports",
        ),
        _control(
            id="gdpr-transfer",
            title="Cross-border transfer controls",
            requirement="Block or alert when EU personal data leaves approved regions.",
            status="met" if has_eu_pii else "not_met",
            evidence="EU residency gate enforced by PII Redaction — EU." if has_eu_pii else None,
            remediation="Enable EU residency rules on the PII Redaction — EU policy bundle.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="gdpr-transparency",
            title="Transparency & lawful basis logging",
            requirement="Log purpose and lawful basis for automated decisions affecting individuals.",
            status="in_progress" if signals.audit_log_count >= 5 else "not_met",
            evidence="Gateway audit trail captures actor, policy, and outcome metadata.",
            remediation="Tag audit exports with lawful-basis fields in Reports.",
            pysetu_module="Reports",
        ),
    ]


def _build_hipaa_controls(signals: TenantComplianceSignals) -> list[DashboardComplianceControl]:
    has_pii = bool({"PII Redaction — EU", "PII Redaction — US"} & signals.active_policy_names)
    has_access_controls = signals.llm_provider_count > 0

    return [
        _control(
            id="hipaa-164308",
            title="§164.308 — Administrative safeguards",
            requirement="Assign security responsibility and enforce role-based access to AI controls.",
            status="met",
            evidence="RBAC roles enforced for tenant users and admin APIs.",
            pysetu_module="Settings",
        ),
        _control(
            id="hipaa-164312",
            title="§164.312 — Technical safeguards",
            requirement="Control access to ePHI in prompts, tool outputs, and model responses.",
            status="met" if has_pii else "not_met",
            evidence="PII/PHI patterns redacted or blocked at the gateway." if has_pii else None,
            remediation="Activate PII redaction policies and block PHI in outbound tool calls.",
            pysetu_module="Data Protection",
        ),
        _control(
            id="hipaa-164314",
            title="§164.314 — Organizational requirements",
            requirement="Track business associate agreements for third-party LLM and MCP vendors.",
            status="not_met",
            remediation="Upload BAA attestations per LLM provider in Integrations settings.",
            pysetu_module="Settings",
        ),
        _control(
            id="hipaa-audit",
            title="Audit controls & integrity",
            requirement="Record who accessed PHI-bearing AI requests and what action was taken.",
            status="met" if signals.audit_log_count >= 10 else "in_progress" if signals.audit_log_count else "not_met",
            evidence=f"{signals.audit_log_count} auditable gateway events in the last 30 days.",
            remediation="Route production AI traffic through PySetu gateway.",
            pysetu_module="Audit Explorer",
        ),
        _control(
            id="hipaa-minimum",
            title="Minimum necessary use",
            requirement="Limit PHI sent to models and MCP tools to the minimum required.",
            status="in_progress" if has_pii else "not_met",
            evidence="Redaction rules reduce PHI surface area in prompts." if has_pii else None,
            remediation="Add field-level redaction rules and MCP tool allowlists.",
            pysetu_module="MCP Governance",
        ),
        _control(
            id="hipaa-transmission",
            title="Transmission security",
            requirement="Encrypt PHI in transit to LLM providers and MCP endpoints.",
            status="met" if has_access_controls else "in_progress",
            evidence="TLS enforced for configured LLM providers." if has_access_controls else None,
            remediation="Register providers with TLS-only endpoints in LLM Router.",
            pysetu_module="LLM Router",
        ),
        _control(
            id="hipaa-incident",
            title="Incident response for PHI exposure",
            requirement="Detect and respond to PHI leakage in model outputs.",
            status="met" if signals.pii_events else "in_progress" if has_pii else "not_met",
            evidence=f"{signals.pii_events} PII-related events detected and handled." if signals.pii_events else None,
            remediation="Enable alert mode on PII policies and review blocked events daily.",
            pysetu_module="Observability",
        ),
        _control(
            id="hipaa-retention",
            title="Retention & disposal",
            requirement="Define retention for audit logs containing PHI metadata.",
            status="not_met",
            remediation="Set audit retention policy and schedule exports in Reports.",
            pysetu_module="Reports",
        ),
    ]


def _build_soc2_controls(signals: TenantComplianceSignals) -> list[DashboardComplianceControl]:
    has_monitoring = signals.audit_log_count >= 5
    has_change_control = "Data Exfiltration Block" in signals.active_policy_names

    return [
        _control(
            id="soc2-cc61",
            title="CC6.1 — Logical access",
            requirement="Restrict configuration changes to authorized admin roles.",
            status="met",
            evidence="Tenant Admin and Security Admin roles gate write APIs.",
            pysetu_module="Settings",
        ),
        _control(
            id="soc2-cc72",
            title="CC7.2 — System monitoring",
            requirement="Monitor AI gateway traffic, blocks, and anomalies continuously.",
            status="met" if has_monitoring else "not_met",
            evidence=f"{signals.total_requests} requests monitored in the last 30 days."
            if signals.total_requests
            else None,
            remediation="Enable Observability dashboards and alert thresholds.",
            pysetu_module="Observability",
        ),
        _control(
            id="soc2-cc81",
            title="CC8.1 — Change management",
            requirement="Track policy and routing changes with approval evidence.",
            status="in_progress" if signals.draft_policy_count else "not_met",
            evidence=f"{signals.draft_policy_count} policies awaiting activation review."
            if signals.draft_policy_count
            else None,
            remediation="Move draft policies through review before activation.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="soc2-c11",
            title="C1.1 — Confidentiality commitments",
            requirement="Prevent unauthorized disclosure via DLP and output inspection.",
            status="met" if has_change_control else "in_progress",
            evidence="Data Exfiltration Block policy active." if has_change_control else None,
            remediation="Activate Data Exfiltration Block and secret detection rules.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="soc2-p11",
            title="P1.1 — Privacy notice alignment",
            requirement="Align AI data use with published privacy commitments.",
            status="in_progress",
            evidence="PII handling rules documented in active policies.",
            remediation="Map each active policy to privacy notice sections in Reports.",
            pysetu_module="Reports",
        ),
        _control(
            id="soc2-availability",
            title="A1.2 — Availability monitoring",
            requirement="Track LLM provider uptime and failover readiness.",
            status="met"
            if signals.llm_provider_count >= 2
            else "in_progress"
            if signals.llm_provider_count
            else "not_met",
            evidence=f"{signals.llm_provider_count} active LLM providers configured.",
            remediation="Register backup providers and weighted routing in LLM Router.",
            pysetu_module="LLM Router",
        ),
        _control(
            id="soc2-vendor",
            title="CC9.2 — Vendor risk for MCP/LLM",
            requirement="Assess and monitor third-party AI integrations.",
            status="met"
            if signals.mcp_server_count and signals.high_risk_mcp_count == 0
            else "in_progress"
            if signals.mcp_server_count
            else "not_met",
            evidence=f"{signals.mcp_server_count} MCP servers tracked; {signals.high_risk_mcp_count} high-risk.",
            remediation="Review MCP risk scores and disable high-risk tools.",
            pysetu_module="MCP Governance",
        ),
        _control(
            id="soc2-incident",
            title="CC7.3 — Incident response",
            requirement="Investigate blocked requests and policy violations.",
            status="met" if signals.blocked_requests else "in_progress",
            evidence=f"{signals.blocked_requests} blocked events available for triage.",
            remediation="Assign on-call rotation for Security Center alerts.",
            pysetu_module="Security Center",
        ),
    ]


def _build_iso_controls(signals: TenantComplianceSignals) -> list[DashboardComplianceControl]:
    has_tool_allowlist = "Tool Allowlist" in signals.active_policy_names

    return [
        _control(
            id="iso-a91",
            title="A.9.1 — Access control policy",
            requirement="Define and enforce access rules for AI administration.",
            status="met",
            evidence="RBAC matrix enforced across UI and API.",
            pysetu_module="Settings",
        ),
        _control(
            id="iso-a124",
            title="A.12.4 — Logging & monitoring",
            requirement="Log security events for AI gateway and MCP activity.",
            status="met" if signals.audit_log_count >= 10 else "in_progress" if signals.audit_log_count else "not_met",
            evidence=f"{signals.audit_log_count} security-relevant audit entries.",
            remediation="Ensure all agents use PySetu gateway keys.",
            pysetu_module="Audit Explorer",
        ),
        _control(
            id="iso-a131",
            title="A.13.1 — Network security for AI traffic",
            requirement="Protect data in transit to external LLM and MCP endpoints.",
            status="met" if signals.llm_provider_count else "not_met",
            evidence="Providers registered with encrypted transport.",
            remediation="Configure TLS-only upstream endpoints.",
            pysetu_module="LLM Router",
        ),
        _control(
            id="iso-a141",
            title="A.14.1 — Secure development of AI workflows",
            requirement="Govern prompt templates and tool usage in Studio.",
            status="in_progress",
            evidence="Policy Studio governs production-bound policies.",
            remediation="Link Studio experiments to approved policy bundles before promotion.",
            pysetu_module="Studio",
        ),
        _control(
            id="iso-a181",
            title="A.18.1 — Compliance with legal requirements",
            requirement="Map controls to GDPR, HIPAA, and regional obligations.",
            status="in_progress",
            evidence="Compliance Center tracks five frameworks.",
            remediation="Attach evidence exports per framework in Reports.",
            pysetu_module="Compliance Center",
        ),
        _control(
            id="iso-a122",
            title="A.12.2 — Malware / abuse protection",
            requirement="Block prompt injection and jailbreak attempts.",
            status="met"
            if {"Prompt Injection Guard", "Jailbreak Prevention"} <= signals.active_policy_names
            else "in_progress",
            evidence="Injection and jailbreak policies enforced at gateway.",
            remediation="Enable Prompt Injection Guard and Jailbreak Prevention.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="iso-a131-mcp",
            title="A.13.2 — MCP tool segregation",
            requirement="Restrict high-risk MCP tools via allowlists.",
            status="met" if has_tool_allowlist else "not_met",
            evidence="Tool Allowlist policy active." if has_tool_allowlist else None,
            remediation="Activate Tool Allowlist under MCP Governance.",
            pysetu_module="MCP Governance",
        ),
        _control(
            id="iso-a161",
            title="A.16.1 — Incident management",
            requirement="Document response steps for AI security incidents.",
            status="in_progress" if signals.blocked_requests else "not_met",
            evidence=f"{signals.blocked_requests} incidents captured for review.",
            remediation="Define severity tiers in Security Center playbooks.",
            pysetu_module="Security Center",
        ),
    ]


def _build_nist_controls(signals: TenantComplianceSignals) -> list[DashboardComplianceControl]:
    has_governance = signals.mcp_server_count > 0 or signals.llm_provider_count > 0
    block_ratio_ok = signals.block_rate <= 15

    return [
        _control(
            id="nist-govern-1",
            title="GOVERN 1 — Policies & accountability",
            requirement="Establish AI governance policies with named owners.",
            status="met" if len(signals.active_policy_names) >= 4 else "in_progress",
            evidence=f"{len(signals.active_policy_names)} active governance policies.",
            remediation="Activate organization policy folders in Policy Studio.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="nist-govern-2",
            title="GOVERN 2 — Risk tolerance",
            requirement="Define acceptable risk for MCP tools and model outputs.",
            status="met"
            if signals.high_risk_mcp_count == 0 and signals.mcp_server_count
            else "in_progress"
            if signals.mcp_server_count
            else "not_met",
            evidence=f"{signals.high_risk_mcp_count} MCP servers above risk threshold.",
            remediation="Remediate or disable high-risk MCP integrations.",
            pysetu_module="MCP Governance",
        ),
        _control(
            id="nist-map-1",
            title="MAP 1 — Context & use-case inventory",
            requirement="Inventory LLM use cases, data classes, and downstream tools.",
            status="met" if has_governance else "not_met",
            evidence="Governance Graph maps policies to agents and tools." if has_governance else None,
            remediation="Register all production agents and MCP servers.",
            pysetu_module="Governance Graph",
        ),
        _control(
            id="nist-map-2",
            title="MAP 2 — Benefits vs. harm analysis",
            requirement="Document trade-offs for high-impact AI workflows.",
            status="not_met",
            remediation="Add harm analysis worksheets to Reports for each agent.",
            pysetu_module="Reports",
        ),
        _control(
            id="nist-measure-1",
            title="MEASURE 1 — Performance & safety metrics",
            requirement="Track block rate, redactions, and model error rates.",
            status="met" if signals.total_requests else "not_met",
            evidence=f"Block rate {signals.block_rate:.1f}% over {signals.total_requests} requests.",
            remediation="Route traffic through gateway to collect baseline metrics.",
            pysetu_module="Observability",
        ),
        _control(
            id="nist-measure-2",
            title="MEASURE 2 — Bias & toxicity thresholds",
            requirement="Monitor toxic content and unsafe completions.",
            status="in_progress" if block_ratio_ok else "not_met",
            evidence="Policy violations tracked in Observability.",
            remediation="Enable toxic content rules and review blocked samples weekly.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="nist-manage-1",
            title="MANAGE 1 — Risk treatment",
            requirement="Apply controls when risks exceed tolerance (block, alert, route).",
            status="met" if signals.blocked_requests else "in_progress",
            evidence=f"{signals.blocked_requests} requests blocked by policy enforcement.",
            remediation="Set enforcement to Block on high-severity rules.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="nist-manage-2",
            title="MANAGE 2 — Continuous improvement",
            requirement="Review policy effectiveness and rebalance routing monthly.",
            status="in_progress",
            evidence="LLM Router supports weighted pools and scheduled rebalance.",
            remediation="Schedule rebalance jobs and review top policies monthly.",
            pysetu_module="LLM Router",
        ),
    ]


def _finalize_framework(name: str, controls: list[DashboardComplianceControl]) -> DashboardComplianceFramework:
    passed = sum(1 for c in controls if c.status == "met")
    in_progress = sum(1 for c in controls if c.status == "in_progress")
    total = len(controls)
    score = round(((passed + in_progress * 0.5) / total) * 100, 1) if total else 0.0
    return DashboardComplianceFramework(
        name=name,
        score=score,
        status=_framework_status(score, passed, total),
        controls=total,
        passed=passed,
        in_progress=in_progress,
        not_met=total - passed - in_progress,
        control_items=controls,
    )


async def build_compliance_frameworks(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    compliance_score: float,
    block_rate: float,
    pii_events: int,
    blocked_requests: int,
    total_requests: int,
    audit_start,
    audit_end,
) -> list[DashboardComplianceFramework]:
    signals = await load_tenant_compliance_signals(
        db,
        tenant_id,
        compliance_score=compliance_score,
        block_rate=block_rate,
        pii_events=pii_events,
        blocked_requests=blocked_requests,
        total_requests=total_requests,
        audit_start=audit_start,
        audit_end=audit_end,
    )

    return [
        _finalize_framework("GDPR", _build_gdpr_controls(signals)),
        _finalize_framework("HIPAA", _build_hipaa_controls(signals)),
        _finalize_framework("SOC 2 Type II", _build_soc2_controls(signals)),
        _finalize_framework("ISO 27001", _build_iso_controls(signals)),
        _finalize_framework("NIST AI RMF", _build_nist_controls(signals)),
    ]
