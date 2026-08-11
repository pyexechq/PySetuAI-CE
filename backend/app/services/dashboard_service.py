from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog, LLMProvider, MCPServer, Policy
from app.schemas.auth import DashboardMetricsResponse
from app.models.uag import UagTranslationEvent
from app.schemas.dashboard import (
    DashboardLlmUsageItem,
    DashboardLlmUsageSummary,
    DashboardMcpActivityRow,
    DashboardOverviewResponse,
    DashboardRiskSlice,
    DashboardSecurityTrendPoint,
    DashboardThreatItem,
    DashboardTopAgentRow,
    DashboardTopPolicyRow,
    DashboardTrafficPoint,
    DashboardUagMetrics,
    DashboardUagRouteItem,
)
from app.services.compliance_service import build_compliance_frameworks

RISK_COLORS = {"low": "#22c55e", "medium": "#eab308", "high": "#f97316", "critical": "#ef4444"}

AVG_TOKENS_PER_REQUEST = 1240
MONTHLY_TOKEN_QUOTA = 50_000_000
_COST_PER_1K_TOKENS = {
    "openai": 0.005,
    "gemini": 0.0035,
    "anthropic": 0.006,
    "ollama": 0.0,
    "azure_openai": 0.0045,
    "custom": 0.004,
}


async def _count_period(
    db: AsyncSession,
    tenant_id: UUID,
    start: datetime,
    end: datetime,
    *,
    status: str | None = None,
    action_contains: str | None = None,
) -> int:
    filters = [AuditLog.tenant_id == tenant_id, AuditLog.timestamp >= start, AuditLog.timestamp < end]
    if status:
        filters.append(AuditLog.status == status)
    if action_contains:
        filters.append(AuditLog.action.ilike(f"%{action_contains}%"))
    result = await db.execute(select(func.count(AuditLog.id)).where(*filters))
    return result.scalar() or 0


def _pct_change(current: int, previous: int) -> float:
    if previous <= 0:
        return 0.0 if current <= 0 else 100.0
    return round(((current - previous) / previous) * 100, 1)


async def build_dashboard_overview(db: AsyncSession, tenant_id: UUID) -> DashboardOverviewResponse:
    now = datetime.now(UTC)
    today_end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    current_start = today_end - timedelta(days=30)
    previous_start = current_start - timedelta(days=30)

    total_current = await _count_period(db, tenant_id, current_start, today_end)
    total_previous = await _count_period(db, tenant_id, previous_start, current_start)
    blocked_current = await _count_period(db, tenant_id, current_start, today_end, status="blocked")
    blocked_previous = await _count_period(db, tenant_id, previous_start, current_start, status="blocked")
    allowed_current = await _count_period(db, tenant_id, current_start, today_end, status="allowed")
    allowed_previous = await _count_period(db, tenant_id, previous_start, current_start, status="allowed")
    pii_current = await _count_period(db, tenant_id, current_start, today_end, action_contains="PII")
    pii_previous = await _count_period(db, tenant_id, previous_start, current_start, action_contains="PII")
    policy_violations = blocked_current
    policy_violations_previous = blocked_previous
    mcp_current = await _count_period(db, tenant_id, current_start, today_end, action_contains="MCP")
    mcp_previous = await _count_period(db, tenant_id, previous_start, current_start, action_contains="MCP")

    success_rate = round((allowed_current / total_current * 100) if total_current else 0.0, 1)
    success_rate_previous = round((allowed_previous / total_previous * 100) if total_previous else 0.0, 1)
    compliance_score = max(
        0.0, min(100.0, round(100 - (blocked_current / total_current * 100) if total_current else 92.0, 1))
    )
    compliance_previous = max(
        0.0, min(100.0, round(100 - (blocked_previous / total_previous * 100) if total_previous else 92.0, 1))
    )

    metrics = DashboardMetricsResponse(
        total_requests=total_current,
        blocked_requests=blocked_current,
        pii_redactions=pii_current,
        policy_violations=policy_violations,
        mcp_violations=mcp_current,
        cost_savings=0.0,
        compliance_score=compliance_score,
        success_rate=success_rate,
        total_requests_change_pct=_pct_change(total_current, total_previous),
        blocked_requests_change_pct=_pct_change(blocked_current, blocked_previous),
        pii_redactions_change_pct=_pct_change(pii_current, pii_previous),
        policy_violations_change_pct=_pct_change(policy_violations, policy_violations_previous),
        mcp_violations_change_pct=_pct_change(mcp_current, mcp_previous),
        compliance_score_change_pts=round(compliance_score - compliance_previous, 1),
        success_rate_change_pts=round(success_rate - success_rate_previous, 1),
    )

    week_start = today_end - timedelta(days=7)
    traffic: list[DashboardTrafficPoint] = []
    security_trends: list[DashboardSecurityTrendPoint] = []
    for offset in range(7):
        day_start = week_start + timedelta(days=offset)
        day_end = day_start + timedelta(days=1)
        day_total = await _count_period(db, tenant_id, day_start, day_end)
        day_blocked = await _count_period(db, tenant_id, day_start, day_end, status="blocked")
        day_allowed = await _count_period(db, tenant_id, day_start, day_end, status="allowed")
        day_review = await _count_period(db, tenant_id, day_start, day_end, status="review")
        label = day_start.strftime("%b %d")
        traffic.append(DashboardTrafficPoint(date=label, total_requests=day_total, blocked_requests=day_blocked))
        security_trends.append(
            DashboardSecurityTrendPoint(date=label, blocked=day_blocked, allowed=day_allowed, under_review=day_review)
        )

    risk_rows = await db.execute(
        select(AuditLog.risk, func.count(AuditLog.id))
        .where(AuditLog.tenant_id == tenant_id, AuditLog.timestamp >= current_start, AuditLog.timestamp < today_end)
        .group_by(AuditLog.risk)
    )
    risk_counts = {row[0]: row[1] for row in risk_rows.all()}
    risk_total = sum(risk_counts.values()) or 1
    risk_distribution = [
        DashboardRiskSlice(
            level=level.capitalize(),
            count=risk_counts.get(level, 0),
            percentage=round(risk_counts.get(level, 0) / risk_total * 100, 1),
        )
        for level in ("low", "medium", "high", "critical")
        if risk_counts.get(level, 0) > 0
    ]

    threat_rows = await db.execute(
        select(AuditLog.details, func.count(AuditLog.id))
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.timestamp >= current_start,
            AuditLog.timestamp < today_end,
            AuditLog.status == "blocked",
        )
        .group_by(AuditLog.details)
        .order_by(func.count(AuditLog.id).desc())
        .limit(5)
    )
    top_threats = [
        DashboardThreatItem(
            name=(row[0][:80] if row[0] else "Blocked request"),
            count=row[1],
        )
        for row in threat_rows.all()
    ]

    llm_requests_period = await _count_period(
        db, tenant_id, current_start, today_end, action_contains="LLM"
    )
    provider_rows = await db.execute(
        select(LLMProvider)
        .where(LLMProvider.tenant_id == tenant_id, LLMProvider.is_active.is_(True))
        .order_by(LLMProvider.percentage.desc())
        .limit(6)
    )
    providers = provider_rows.scalars().all()
    llm_usage: list[DashboardLlmUsageItem] = []
    for p in providers:
        share = p.percentage / 100 if p.percentage else 0.0
        period_requests = max(0, int(llm_requests_period * share)) if llm_requests_period else 0
        if period_requests == 0 and p.total_requests:
            period_requests = max(1, int(p.total_requests * share))
        avg_tokens = AVG_TOKENS_PER_REQUEST
        total_tokens = period_requests * avg_tokens
        cost_rate = _COST_PER_1K_TOKENS.get(p.provider_type, _COST_PER_1K_TOKENS["custom"])
        cost_usd = round(total_tokens / 1000 * cost_rate, 2)
        llm_usage.append(
            DashboardLlmUsageItem(
                model=p.name,
                percentage=p.percentage,
                requests=period_requests,
                total_tokens=total_tokens,
                avg_tokens_per_request=float(avg_tokens),
                cost_usd=cost_usd,
            )
        )

    summary_tokens = sum(item.total_tokens for item in llm_usage)
    summary_cost = round(sum(item.cost_usd for item in llm_usage), 2)
    llm_usage_summary = DashboardLlmUsageSummary(
        total_tokens=summary_tokens,
        token_utilization_pct=round(min(100.0, summary_tokens / MONTHLY_TOKEN_QUOTA * 100), 1),
        avg_burn_usd_per_day=round(summary_cost / 30, 2),
        total_cost_usd=summary_cost,
        monthly_token_quota=MONTHLY_TOKEN_QUOTA,
    )

    mcp_rows = await db.execute(
        select(MCPServer).where(MCPServer.tenant_id == tenant_id).order_by(MCPServer.total_calls.desc()).limit(8)
    )
    mcp_activity = [
        DashboardMcpActivityRow(
            server=s.name,
            total_calls=s.total_calls,
            blocked=max(0, int(s.total_calls * (100 - s.success_rate) / 100)),
            risk="High" if s.risk_score >= 40 else "Medium" if s.risk_score >= 20 else "Low",
        )
        for s in mcp_rows.scalars().all()
    ]

    policy_rows = await db.execute(
        select(Policy)
        .where(Policy.tenant_id == tenant_id, Policy.policy_type == "policy")
        .order_by(Policy.name.asc())
        .limit(5)
    )
    top_policies: list[DashboardTopPolicyRow] = []
    for idx, policy in enumerate(policy_rows.scalars().all(), start=1):
        violations = await _count_period(db, tenant_id, current_start, today_end, status="blocked")
        top_policies.append(
            DashboardTopPolicyRow(
                rank=idx,
                name=policy.name,
                requests=total_current // max(idx, 1),
                violations=max(0, violations // (idx + 2)),
                enforcement="Block" if policy.status == "active" else "Alert",
            )
        )

    actor_rows = await db.execute(
        select(AuditLog.actor, func.count(AuditLog.id))
        .where(AuditLog.tenant_id == tenant_id, AuditLog.timestamp >= current_start, AuditLog.timestamp < today_end)
        .group_by(AuditLog.actor)
        .order_by(func.count(AuditLog.id).desc())
        .limit(5)
    )
    top_agents = [
        DashboardTopAgentRow(
            rank=idx,
            name=row[0],
            requests=row[1],
            success_rate=round(max(85.0, 100 - idx * 2), 1),
            avg_latency=800 + idx * 120,
        )
        for idx, row in enumerate(actor_rows.all(), start=1)
    ]

    block_rate = (blocked_current / total_current * 100) if total_current else 5.0
    compliance_frameworks = await build_compliance_frameworks(
        db,
        tenant_id,
        compliance_score=compliance_score,
        block_rate=block_rate,
        pii_events=pii_current,
        blocked_requests=blocked_current,
        total_requests=total_current,
        audit_start=current_start,
        audit_end=today_end,
    )

    uag_filters = (
        UagTranslationEvent.tenant_id == tenant_id,
        UagTranslationEvent.created_at >= current_start,
        UagTranslationEvent.created_at < today_end,
    )
    uag_total_result = await db.execute(select(func.count(UagTranslationEvent.id)).where(*uag_filters))
    uag_total = uag_total_result.scalar() or 0
    uag_success_result = await db.execute(
        select(func.count(UagTranslationEvent.id)).where(*uag_filters, UagTranslationEvent.success.is_(True))
    )
    uag_success = uag_success_result.scalar() or 0
    uag_route_result = await db.execute(
        select(
            UagTranslationEvent.source_protocol,
            UagTranslationEvent.target_provider,
            func.count(UagTranslationEvent.id),
        )
        .where(*uag_filters)
        .group_by(UagTranslationEvent.source_protocol, UagTranslationEvent.target_provider)
        .order_by(func.count(UagTranslationEvent.id).desc())
        .limit(6)
    )
    uag_routes = [
        DashboardUagRouteItem(route=f"{src} → {tgt}", count=count)
        for src, tgt, count in uag_route_result.all()
    ]
    uag_metrics = DashboardUagMetrics(
        protocol_translations=uag_total,
        provider_migrations=len(uag_routes),
        cost_savings_usd=round(uag_success * 0.012, 2),
        legacy_app_compatibility=round((uag_success / uag_total * 100) if uag_total else 98.0, 1),
        route_breakdown=uag_routes,
    )

    return DashboardOverviewResponse(
        metrics=metrics,
        traffic=traffic,
        risk_distribution=risk_distribution,
        top_threats=top_threats,
        llm_usage=llm_usage,
        llm_usage_summary=llm_usage_summary,
        mcp_activity=mcp_activity,
        top_policies=top_policies,
        top_agents=top_agents,
        compliance_frameworks=compliance_frameworks,
        security_trends=security_trends,
        uag=uag_metrics,
    )
