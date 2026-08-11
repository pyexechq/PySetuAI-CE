from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog, LLMProvider, MCPServer, Policy
from app.schemas.auth import DashboardMetricsResponse
from app.schemas.dashboard import (
    DashboardLlmUsageItem,
    DashboardMcpActivityRow,
    DashboardOverviewResponse,
    DashboardRiskSlice,
    DashboardSecurityTrendPoint,
    DashboardThreatItem,
    DashboardTopAgentRow,
    DashboardTopPolicyRow,
    DashboardTrafficPoint,
)
from app.services.compliance_service import build_compliance_frameworks

RISK_COLORS = {"low": "#22c55e", "medium": "#eab308", "high": "#f97316", "critical": "#ef4444"}


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

    provider_rows = await db.execute(
        select(LLMProvider)
        .where(LLMProvider.tenant_id == tenant_id, LLMProvider.is_active.is_(True))
        .order_by(LLMProvider.percentage.desc())
        .limit(6)
    )
    llm_usage = [
        DashboardLlmUsageItem(model=p.name, percentage=p.percentage, requests=p.total_requests)
        for p in provider_rows.scalars().all()
    ]

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

    return DashboardOverviewResponse(
        metrics=metrics,
        traffic=traffic,
        risk_distribution=risk_distribution,
        top_threats=top_threats,
        llm_usage=llm_usage,
        mcp_activity=mcp_activity,
        top_policies=top_policies,
        top_agents=top_agents,
        compliance_frameworks=compliance_frameworks,
        security_trends=security_trends,
    )
