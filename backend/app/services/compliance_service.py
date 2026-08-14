"""Compliance framework scoring and per-control evaluation for the Compliance Center."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog, LLMProvider, MCPServer, Policy, PromptTemplate
from app.models.tenant import Tenant
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
    request_log_retention_days: int = 0
    prompt_template_count: int = 0


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

    tenant = await db.get(Tenant, tenant_id)
    request_log_retention_days = tenant.request_log_retention_days if tenant else 0

    prompt_count_result = await db.execute(
        select(func.count(PromptTemplate.id)).where(
            PromptTemplate.tenant_id == tenant_id,
            PromptTemplate.is_active.is_(True),
        )
    )
    prompt_template_count = prompt_count_result.scalar() or 0

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
        request_log_retention_days=request_log_retention_days,
        prompt_template_count=prompt_template_count,
    )


def _eval(
    *,
    met: bool,
    progressing: bool = False,
    met_evidence: str | None = None,
    progress_evidence: str | None = None,
) -> tuple[ControlStatus, str | None]:
    if met:
        return "met", met_evidence
    if progressing:
        return "in_progress", progress_evidence
    return "not_met", None


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
    has_dlp_active = "DLP Classification" in signals.active_policy_names
    has_jailbreak = "Jailbreak Prevention" in signals.active_policy_names
    art25_status, art25_evidence = _eval(
        met=has_eu_pii and has_us_pii,
        progressing=has_eu_pii or has_us_pii,
        met_evidence="Active PII redaction policies at the gateway (EU and US).",
        progress_evidence="PII redaction is active for one region; enable the remaining regional policy.",
    )
    art30_status, art30_evidence = _eval(
        met=signals.audit_log_count >= 10,
        progressing=signals.audit_log_count > 0,
        met_evidence=f"{signals.audit_log_count} audit events captured in the last 30 days.",
        progress_evidence=f"{signals.audit_log_count} audit events captured; continue routing traffic through the gateway.",
    )
    art32_status, art32_evidence = _eval(
        met=has_jailbreak,
        progressing=bool(signals.active_policy_names),
        met_evidence="Jailbreak Prevention is active at the AI gateway.",
        progress_evidence="Gateway policies are active; enable Jailbreak Prevention to complete this control.",
    )
    art17_status, art17_evidence = _eval(
        met=False,
        progressing=signals.request_log_retention_days > 0,
        progress_evidence=(
            f"Request-log retention is {signals.request_log_retention_days} days. "
            "Document the erasure runbook to complete this control."
        ),
    )
    art33_status, art33_evidence = _eval(
        met=False,
        progressing=signals.blocked_requests > 0,
        progress_evidence=f"{signals.blocked_requests} blocked events available for incident review.",
    )
    art35_status, art35_evidence = _eval(
        met=has_dlp_active,
        progressing=signals.draft_policy_count > 0,
        met_evidence="DLP Classification policy is active for high-risk AI processing.",
        progress_evidence="DLP classification is drafted; activate the policy to complete DPIA coverage.",
    )
    transfer_status, transfer_evidence = _eval(
        met=has_eu_pii,
        progressing=False,
        met_evidence="EU residency gate enforced by PII Redaction — EU.",
    )
    transparency_status, transparency_evidence = _eval(
        met=signals.audit_log_count >= 10,
        progressing=signals.audit_log_count >= 5,
        met_evidence="Gateway audit trail captures actor, policy, and outcome metadata.",
        progress_evidence="Audit trail is populating; tag exports with lawful-basis fields in Reports.",
    )

    return [
        _control(
            id="gdpr-art25",
            title="Art. 25 — Data protection by design",
            requirement="Embed privacy controls in AI gateway and policy enforcement before data reaches models.",
            status=art25_status,
            evidence=art25_evidence,
            remediation="Activate PII Redaction — EU and US policies in Policy Studio.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="gdpr-art30",
            title="Art. 30 — Records of processing",
            requirement="Maintain auditable records of AI requests, policy actions, and data classifications.",
            status=art30_status,
            evidence=art30_evidence,
            remediation="Enable gateway traffic and route requests through PySetu to populate Audit Explorer.",
            pysetu_module="Audit Explorer",
        ),
        _control(
            id="gdpr-art32",
            title="Art. 32 — Security of processing",
            requirement="Apply technical measures (encryption, access control, prompt/output inspection).",
            status=art32_status,
            evidence=art32_evidence,
            remediation="Enable Jailbreak Prevention and Prompt Injection Guard policies.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="gdpr-art17",
            title="Art. 17 — Right to erasure workflow",
            requirement="Document and execute erasure requests for personal data used in AI workflows.",
            status=art17_status,
            evidence=art17_evidence,
            remediation="Define an erasure runbook and link retention policies to audit log purge schedules.",
            pysetu_module="Settings",
        ),
        _control(
            id="gdpr-art33",
            title="Art. 33 — Breach notification readiness",
            requirement="Detect incidents within 72 hours and maintain an escalation path.",
            status=art33_status,
            evidence=art33_evidence,
            remediation="Configure alert routing in Observability and document breach notification owners.",
            pysetu_module="Observability",
        ),
        _control(
            id="gdpr-art35",
            title="Art. 35 — DPIA for high-risk AI",
            requirement="Complete a Data Protection Impact Assessment for high-risk LLM use cases.",
            status=art35_status,
            evidence=art35_evidence,
            remediation="Finalize DLP Classification policy and attach DPIA evidence in Reports.",
            pysetu_module="Reports",
        ),
        _control(
            id="gdpr-transfer",
            title="Cross-border transfer controls",
            requirement="Block or alert when EU personal data leaves approved regions.",
            status=transfer_status,
            evidence=transfer_evidence,
            remediation="Enable EU residency rules on the PII Redaction — EU policy bundle.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="gdpr-transparency",
            title="Transparency & lawful basis logging",
            requirement="Log purpose and lawful basis for automated decisions affecting individuals.",
            status=transparency_status,
            evidence=transparency_evidence,
            remediation="Tag audit exports with lawful-basis fields in Reports.",
            pysetu_module="Reports",
        ),
    ]


def _build_hipaa_controls(signals: TenantComplianceSignals) -> list[DashboardComplianceControl]:
    has_pii = bool({"PII Redaction — EU", "PII Redaction — US"} & signals.active_policy_names)
    has_tool_allowlist = "Tool Allowlist" in signals.active_policy_names
    has_access_controls = signals.llm_provider_count > 0
    tech_status, tech_evidence = _eval(
        met=has_pii,
        met_evidence="PII/PHI patterns redacted or blocked at the gateway.",
    )
    org_status, org_evidence = _eval(
        met=False,
        progressing=signals.llm_provider_count > 0 or signals.mcp_server_count > 0,
        progress_evidence=(
            f"{signals.llm_provider_count} LLM providers and {signals.mcp_server_count} MCP servers registered. "
            "Attach BAA attestations in Integrations."
        ),
    )
    audit_status, audit_evidence = _eval(
        met=signals.audit_log_count >= 10,
        progressing=signals.audit_log_count > 0,
        met_evidence=f"{signals.audit_log_count} auditable gateway events in the last 30 days.",
        progress_evidence=f"{signals.audit_log_count} auditable events captured so far.",
    )
    minimum_status, minimum_evidence = _eval(
        met=has_pii and has_tool_allowlist,
        progressing=has_pii,
        met_evidence="Redaction rules and MCP tool allowlists limit PHI sent to models.",
        progress_evidence="Redaction rules reduce PHI in prompts; add MCP tool allowlists to complete this control.",
    )
    tx_status, tx_evidence = _eval(
        met=has_access_controls,
        progressing=True,
        met_evidence="TLS enforced for configured LLM providers.",
        progress_evidence="Register providers with TLS-only endpoints in LLM Router.",
    )
    incident_status, incident_evidence = _eval(
        met=signals.pii_events > 0,
        progressing=has_pii,
        met_evidence=f"{signals.pii_events} PII-related events detected and handled.",
        progress_evidence="PII policies are active; review blocked events to complete incident response.",
    )
    retention_status, retention_evidence = _eval(
        met=signals.request_log_retention_days > 0,
        met_evidence=f"Audit request logs retained for {signals.request_log_retention_days} days.",
    )

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
            status=tech_status,
            evidence=tech_evidence,
            remediation="Activate PII redaction policies and block PHI in outbound tool calls.",
            pysetu_module="Data Protection",
        ),
        _control(
            id="hipaa-164314",
            title="§164.314 — Organizational requirements",
            requirement="Track business associate agreements for third-party LLM and MCP vendors.",
            status=org_status,
            evidence=org_evidence,
            remediation="Upload BAA attestations per LLM provider in Integrations settings.",
            pysetu_module="Settings",
        ),
        _control(
            id="hipaa-audit",
            title="Audit controls & integrity",
            requirement="Record who accessed PHI-bearing AI requests and what action was taken.",
            status=audit_status,
            evidence=audit_evidence,
            remediation="Route production AI traffic through PySetu gateway.",
            pysetu_module="Audit Explorer",
        ),
        _control(
            id="hipaa-minimum",
            title="Minimum necessary use",
            requirement="Limit PHI sent to models and MCP tools to the minimum required.",
            status=minimum_status,
            evidence=minimum_evidence,
            remediation="Add field-level redaction rules and MCP tool allowlists.",
            pysetu_module="MCP Governance",
        ),
        _control(
            id="hipaa-transmission",
            title="Transmission security",
            requirement="Encrypt PHI in transit to LLM providers and MCP endpoints.",
            status=tx_status,
            evidence=tx_evidence,
            remediation="Register providers with TLS-only endpoints in LLM Router.",
            pysetu_module="LLM Router",
        ),
        _control(
            id="hipaa-incident",
            title="Incident response for PHI exposure",
            requirement="Detect and respond to PHI leakage in model outputs.",
            status=incident_status,
            evidence=incident_evidence,
            remediation="Enable alert mode on PII policies and review blocked events daily.",
            pysetu_module="Observability",
        ),
        _control(
            id="hipaa-retention",
            title="Retention & disposal",
            requirement="Define retention for audit logs containing PHI metadata.",
            status=retention_status,
            evidence=retention_evidence,
            remediation="Set audit retention policy and schedule exports in Reports.",
            pysetu_module="Reports",
        ),
    ]


def _build_soc2_controls(signals: TenantComplianceSignals) -> list[DashboardComplianceControl]:
    has_monitoring = signals.audit_log_count >= 5
    has_exfil = "Data Exfiltration Block" in signals.active_policy_names
    has_pii = bool({"PII Redaction — EU", "PII Redaction — US"} & signals.active_policy_names)
    monitor_status, monitor_evidence = _eval(
        met=has_monitoring,
        progressing=signals.total_requests > 0,
        met_evidence=f"{signals.total_requests} requests monitored in the last 30 days.",
        progress_evidence=f"{signals.total_requests} requests seen; continue collecting a full monitoring window.",
    )
    change_status, change_evidence = _eval(
        met=bool(signals.active_policy_names) and signals.draft_policy_count == 0,
        progressing=signals.draft_policy_count > 0,
        met_evidence=f"{len(signals.active_policy_names)} active policies with none waiting for activation.",
        progress_evidence=f"{signals.draft_policy_count} policies awaiting activation review.",
    )
    conf_status, conf_evidence = _eval(
        met=has_exfil,
        progressing=bool(signals.active_policy_names),
        met_evidence="Data Exfiltration Block policy active.",
        progress_evidence="Activate Data Exfiltration Block and secret detection rules.",
    )
    privacy_status, privacy_evidence = _eval(
        met=has_pii,
        progressing=bool(signals.active_policy_names),
        met_evidence="PII handling rules in active policies align AI data use with privacy commitments.",
        progress_evidence="Map each active policy to privacy notice sections in Reports.",
    )
    avail_status, avail_evidence = _eval(
        met=signals.llm_provider_count >= 2,
        progressing=signals.llm_provider_count > 0,
        met_evidence=f"{signals.llm_provider_count} active LLM providers configured for failover.",
        progress_evidence=f"{signals.llm_provider_count} provider configured; register a backup in LLM Router.",
    )
    vendor_status, vendor_evidence = _eval(
        met=bool(signals.mcp_server_count) and signals.high_risk_mcp_count == 0,
        progressing=signals.mcp_server_count > 0,
        met_evidence=f"{signals.mcp_server_count} MCP servers tracked; none above the high-risk threshold.",
        progress_evidence=f"{signals.mcp_server_count} MCP servers tracked; {signals.high_risk_mcp_count} high-risk.",
    )
    incident_status, incident_evidence = _eval(
        met=signals.blocked_requests > 0,
        progressing=True,
        met_evidence=f"{signals.blocked_requests} blocked events available for triage.",
        progress_evidence="Assign on-call rotation for Security Center alerts.",
    )

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
            status=monitor_status,
            evidence=monitor_evidence,
            remediation="Enable Observability dashboards and alert thresholds.",
            pysetu_module="Observability",
        ),
        _control(
            id="soc2-cc81",
            title="CC8.1 — Change management",
            requirement="Track policy and routing changes with approval evidence.",
            status=change_status,
            evidence=change_evidence,
            remediation="Move draft policies through review before activation.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="soc2-c11",
            title="C1.1 — Confidentiality commitments",
            requirement="Prevent unauthorized disclosure via DLP and output inspection.",
            status=conf_status,
            evidence=conf_evidence,
            remediation="Activate Data Exfiltration Block and secret detection rules.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="soc2-p11",
            title="P1.1 — Privacy notice alignment",
            requirement="Align AI data use with published privacy commitments.",
            status=privacy_status,
            evidence=privacy_evidence,
            remediation="Map each active policy to privacy notice sections in Reports.",
            pysetu_module="Reports",
        ),
        _control(
            id="soc2-availability",
            title="A1.2 — Availability monitoring",
            requirement="Track LLM provider uptime and failover readiness.",
            status=avail_status,
            evidence=avail_evidence,
            remediation="Register backup providers and weighted routing in LLM Router.",
            pysetu_module="LLM Router",
        ),
        _control(
            id="soc2-vendor",
            title="CC9.2 — Vendor risk for MCP/LLM",
            requirement="Assess and monitor third-party AI integrations.",
            status=vendor_status,
            evidence=vendor_evidence,
            remediation="Review MCP risk scores and disable high-risk tools.",
            pysetu_module="MCP Governance",
        ),
        _control(
            id="soc2-incident",
            title="CC7.3 — Incident response",
            requirement="Investigate blocked requests and policy violations.",
            status=incident_status,
            evidence=incident_evidence,
            remediation="Assign on-call rotation for Security Center alerts.",
            pysetu_module="Security Center",
        ),
    ]


def _build_iso_controls(signals: TenantComplianceSignals) -> list[DashboardComplianceControl]:
    has_tool_allowlist = "Tool Allowlist" in signals.active_policy_names
    has_injection = "Prompt Injection Guard" in signals.active_policy_names
    has_jailbreak = "Jailbreak Prevention" in signals.active_policy_names
    log_status, log_evidence = _eval(
        met=signals.audit_log_count >= 10,
        progressing=signals.audit_log_count > 0,
        met_evidence=f"{signals.audit_log_count} security-relevant audit entries.",
        progress_evidence=f"{signals.audit_log_count} security-relevant audit entries captured so far.",
    )
    net_status, net_evidence = _eval(
        met=signals.llm_provider_count > 0,
        met_evidence="Providers registered with encrypted transport.",
    )
    dev_status, dev_evidence = _eval(
        met=signals.prompt_template_count > 0,
        progressing=bool(signals.active_policy_names),
        met_evidence=f"{signals.prompt_template_count} governed prompt templates in Studio.",
        progress_evidence="Policy Studio governs production-bound policies; add prompt templates in Studio.",
    )
    legal_status, legal_evidence = _eval(
        met=len(signals.active_policy_names) >= 4,
        progressing=bool(signals.active_policy_names),
        met_evidence="Compliance Center maps active policies across GDPR, HIPAA, and related obligations.",
        progress_evidence="Activate remaining organization policies and attach evidence exports in Reports.",
    )
    abuse_status, abuse_evidence = _eval(
        met=has_injection and has_jailbreak,
        progressing=has_injection or has_jailbreak,
        met_evidence="Prompt Injection Guard and Jailbreak Prevention are both enforced at the gateway.",
        progress_evidence=(
            "Prompt Injection Guard is active."
            if has_injection and not has_jailbreak
            else "Jailbreak Prevention is active."
            if has_jailbreak
            else None
        ),
    )
    mcp_status, mcp_evidence = _eval(
        met=has_tool_allowlist,
        met_evidence="Tool Allowlist policy active.",
    )
    incident_status, incident_evidence = _eval(
        met=False,
        progressing=signals.blocked_requests > 0,
        progress_evidence=f"{signals.blocked_requests} incidents captured for review.",
    )

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
            status=log_status,
            evidence=log_evidence,
            remediation="Ensure all agents use PySetu gateway keys.",
            pysetu_module="Audit Explorer",
        ),
        _control(
            id="iso-a131",
            title="A.13.1 — Network security for AI traffic",
            requirement="Protect data in transit to external LLM and MCP endpoints.",
            status=net_status,
            evidence=net_evidence,
            remediation="Configure TLS-only upstream endpoints.",
            pysetu_module="LLM Router",
        ),
        _control(
            id="iso-a141",
            title="A.14.1 — Secure development of AI workflows",
            requirement="Govern prompt templates and tool usage in Studio.",
            status=dev_status,
            evidence=dev_evidence,
            remediation="Link Studio experiments to approved policy bundles before promotion.",
            pysetu_module="Studio",
        ),
        _control(
            id="iso-a181",
            title="A.18.1 — Compliance with legal requirements",
            requirement="Map controls to GDPR, HIPAA, and regional obligations.",
            status=legal_status,
            evidence=legal_evidence,
            remediation="Attach evidence exports per framework in Reports.",
            pysetu_module="Compliance Center",
        ),
        _control(
            id="iso-a122",
            title="A.12.2 — Malware / abuse protection",
            requirement="Block prompt injection and jailbreak attempts.",
            status=abuse_status,
            evidence=abuse_evidence,
            remediation="Enable Prompt Injection Guard and Jailbreak Prevention.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="iso-a131-mcp",
            title="A.13.2 — MCP tool segregation",
            requirement="Restrict high-risk MCP tools via allowlists.",
            status=mcp_status,
            evidence=mcp_evidence,
            remediation="Activate Tool Allowlist under MCP Governance.",
            pysetu_module="MCP Governance",
        ),
        _control(
            id="iso-a161",
            title="A.16.1 — Incident management",
            requirement="Document response steps for AI security incidents.",
            status=incident_status,
            evidence=incident_evidence,
            remediation="Define severity tiers in Security Center playbooks.",
            pysetu_module="Security Center",
        ),
    ]


def _build_nist_controls(signals: TenantComplianceSignals) -> list[DashboardComplianceControl]:
    has_governance = signals.mcp_server_count > 0 or signals.llm_provider_count > 0
    govern1_status, govern1_evidence = _eval(
        met=len(signals.active_policy_names) >= 4,
        progressing=bool(signals.active_policy_names),
        met_evidence=f"{len(signals.active_policy_names)} active governance policies.",
        progress_evidence=f"{len(signals.active_policy_names)} active policies; activate remaining organization folders.",
    )
    govern2_status, govern2_evidence = _eval(
        met=bool(signals.mcp_server_count) and signals.high_risk_mcp_count == 0,
        progressing=signals.mcp_server_count > 0,
        met_evidence=f"{signals.mcp_server_count} MCP servers within risk tolerance.",
        progress_evidence=f"{signals.high_risk_mcp_count} MCP servers above risk threshold.",
    )
    map1_status, map1_evidence = _eval(
        met=has_governance,
        met_evidence="Governance Graph maps policies to agents and tools.",
    )
    map2_status, map2_evidence = _eval(
        met=False,
        progressing=has_governance,
        progress_evidence="Use-case inventory exists; add harm-analysis worksheets in Reports.",
    )
    measure1_status, measure1_evidence = _eval(
        met=signals.total_requests > 0,
        met_evidence=f"Block rate {signals.block_rate:.1f}% over {signals.total_requests} requests.",
    )
    measure2_status, measure2_evidence = _eval(
        met=signals.blocked_requests > 0 or signals.pii_events > 0,
        progressing=signals.total_requests > 0,
        met_evidence="Unsafe completions and policy violations are monitored in Observability.",
        progress_evidence="Traffic is flowing; enable toxic-content rules to complete this control.",
    )
    manage1_status, manage1_evidence = _eval(
        met=signals.blocked_requests > 0,
        progressing=bool(signals.active_policy_names),
        met_evidence=f"{signals.blocked_requests} requests blocked by policy enforcement.",
        progress_evidence="Set enforcement to Block on high-severity rules.",
    )
    manage2_status, manage2_evidence = _eval(
        met=signals.llm_provider_count > 0,
        progressing=True,
        met_evidence="LLM Router supports weighted pools and scheduled rebalance.",
        progress_evidence="Schedule rebalance jobs and review top policies monthly.",
    )

    return [
        _control(
            id="nist-govern-1",
            title="GOVERN 1 — Policies & accountability",
            requirement="Establish AI governance policies with named owners.",
            status=govern1_status,
            evidence=govern1_evidence,
            remediation="Activate organization policy folders in Policy Studio.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="nist-govern-2",
            title="GOVERN 2 — Risk tolerance",
            requirement="Define acceptable risk for MCP tools and model outputs.",
            status=govern2_status,
            evidence=govern2_evidence,
            remediation="Remediate or disable high-risk MCP integrations.",
            pysetu_module="MCP Governance",
        ),
        _control(
            id="nist-map-1",
            title="MAP 1 — Context & use-case inventory",
            requirement="Inventory LLM use cases, data classes, and downstream tools.",
            status=map1_status,
            evidence=map1_evidence,
            remediation="Register all production agents and MCP servers.",
            pysetu_module="Governance Graph",
        ),
        _control(
            id="nist-map-2",
            title="MAP 2 — Benefits vs. harm analysis",
            requirement="Document trade-offs for high-impact AI workflows.",
            status=map2_status,
            evidence=map2_evidence,
            remediation="Add harm analysis worksheets to Reports for each agent.",
            pysetu_module="Reports",
        ),
        _control(
            id="nist-measure-1",
            title="MEASURE 1 — Performance & safety metrics",
            requirement="Track block rate, redactions, and model error rates.",
            status=measure1_status,
            evidence=measure1_evidence,
            remediation="Route traffic through gateway to collect baseline metrics.",
            pysetu_module="Observability",
        ),
        _control(
            id="nist-measure-2",
            title="MEASURE 2 — Bias & toxicity thresholds",
            requirement="Monitor toxic content and unsafe completions.",
            status=measure2_status,
            evidence=measure2_evidence,
            remediation="Enable toxic content rules and review blocked samples weekly.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="nist-manage-1",
            title="MANAGE 1 — Risk treatment",
            requirement="Apply controls when risks exceed tolerance (block, alert, route).",
            status=manage1_status,
            evidence=manage1_evidence,
            remediation="Set enforcement to Block on high-severity rules.",
            pysetu_module="Policy Studio",
        ),
        _control(
            id="nist-manage-2",
            title="MANAGE 2 — Continuous improvement",
            requirement="Review policy effectiveness and rebalance routing monthly.",
            status=manage2_status,
            evidence=manage2_evidence,
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
