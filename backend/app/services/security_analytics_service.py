"""Security Center analytics from audit logs and threat detection."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog
from app.schemas.security import (
    SecurityDetectionItem,
    SecurityOverviewResponse,
    SecurityScanMatch,
    SecurityScanRequest,
    SecurityScanResponse,
    SecurityThreatBreakdown,
    SecurityTrendPoint,
)
from app.services.injection_detection_service import THREAT_RULES, categorize_audit_event, scan_content


async def build_security_overview(db: AsyncSession, tenant_id: uuid.UUID) -> SecurityOverviewResponse:
    now = datetime.now(UTC)
    week_end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    week_start = week_end - timedelta(days=7)
    month_start = week_end - timedelta(days=30)

    month_rows = await db.execute(
        select(AuditLog).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.timestamp >= month_start,
            AuditLog.timestamp < week_end,
            AuditLog.status == "blocked",
        )
    )
    blocked_logs = list(month_rows.scalars().all())

    counts = {
        "prompt_injection": 0,
        "jailbreak": 0,
        "data_exfiltration": 0,
        "secret_leakage": 0,
    }
    for log in blocked_logs:
        category = categorize_audit_event(
            action=log.action,
            resource=log.resource,
            details=log.details,
            status=log.status,
        )
        if category:
            counts[category] += 1

    total_threats = sum(counts.values()) or 1
    breakdown = [
        SecurityThreatBreakdown(
            category=cat,
            label=label,
            count=counts[cat],
            percentage=round(counts[cat] / total_threats * 100, 1),
        )
        for cat, label in (
            ("prompt_injection", "Prompt injection"),
            ("jailbreak", "Jailbreak"),
            ("data_exfiltration", "Data exfiltration"),
            ("secret_leakage", "Secret leakage"),
        )
    ]

    recent: list[SecurityDetectionItem] = []
    for log in sorted(blocked_logs, key=lambda row: row.timestamp, reverse=True)[:12]:
        category = categorize_audit_event(
            action=log.action,
            resource=log.resource,
            details=log.details,
            status=log.status,
        )
        if category is None:
            continue
        recent.append(
            SecurityDetectionItem(
                id=str(log.id),
                timestamp=log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                category=category,
                actor=log.actor,
                action=log.action,
                resource=log.resource,
                risk=log.risk,
                details=log.details[:240],
            )
        )

    trends: list[SecurityTrendPoint] = []
    for offset in range(7):
        day_start = week_start + timedelta(days=offset)
        day_end = day_start + timedelta(days=1)
        day_rows = await db.execute(
            select(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.timestamp >= day_start,
                AuditLog.timestamp < day_end,
                AuditLog.status == "blocked",
            )
        )
        day_counts = {"prompt_injection": 0, "jailbreak": 0, "data_exfiltration": 0, "secret_leakage": 0}
        for log in day_rows.scalars().all():
            cat = categorize_audit_event(
                action=log.action,
                resource=log.resource,
                details=log.details,
                status=log.status,
            )
            if cat:
                day_counts[cat] += 1
        trends.append(
            SecurityTrendPoint(
                date=day_start.strftime("%b %d"),
                prompt_injection=day_counts["prompt_injection"],
                jailbreak=day_counts["jailbreak"],
                data_exfiltration=day_counts["data_exfiltration"],
                secret_leakage=day_counts["secret_leakage"],
            )
        )

    rules_active = len(THREAT_RULES)
    return SecurityOverviewResponse(
        threats_blocked_30d=sum(counts.values()),
        rules_active=rules_active,
        breakdown=breakdown,
        recent_detections=recent,
        threat_trends=trends,
    )


def run_security_scan(payload: SecurityScanRequest) -> SecurityScanResponse:
    result = scan_content(payload.content)
    return SecurityScanResponse(
        detected=result.detected,
        recommended_action=result.recommended_action,
        highest_severity=result.highest_severity,
        matches=[
            SecurityScanMatch(
                rule_id=m.rule_id,
                name=m.name,
                category=m.category,
                severity=m.severity,
                detail=m.detail,
            )
            for m in result.matches
        ],
    )
