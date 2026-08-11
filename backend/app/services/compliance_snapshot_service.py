"""Persist and export compliance evidence snapshots for auditors."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog, ComplianceSnapshot
from app.models.tenant import User
from app.schemas.dashboard import DashboardComplianceFramework
from app.services.compliance_service import build_compliance_frameworks


async def _load_compliance_metrics(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    period_days: int = 30,
) -> tuple[list[DashboardComplianceFramework], datetime, datetime, float, int, int]:
    now = datetime.now(UTC)
    period_end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    period_start = period_end - timedelta(days=period_days)

    from sqlalchemy import func

    base = [
        AuditLog.tenant_id == tenant_id,
        AuditLog.timestamp >= period_start,
        AuditLog.timestamp < period_end,
    ]

    total = (await db.execute(select(func.count(AuditLog.id)).where(*base))).scalar() or 0
    blocked = (
        await db.execute(select(func.count(AuditLog.id)).where(*base, AuditLog.status == "blocked"))
    ).scalar() or 0
    pii = (await db.execute(select(func.count(AuditLog.id)).where(*base, AuditLog.action.ilike("%PII%")))).scalar() or 0

    block_rate = (blocked / total * 100) if total else 5.0
    compliance_score = max(
        0.0,
        min(100.0, round(100 - (blocked / total * 100) if total else 92.0, 1)),
    )

    frameworks = await build_compliance_frameworks(
        db,
        tenant_id,
        compliance_score=compliance_score,
        block_rate=block_rate,
        pii_events=pii,
        blocked_requests=blocked,
        total_requests=total,
        audit_start=period_start,
        audit_end=period_end,
    )
    overall = round(sum(f.score for f in frameworks) / len(frameworks), 1) if frameworks else 0.0
    compliant = sum(1 for f in frameworks if f.status == "compliant")
    return frameworks, period_start, period_end, overall, compliant, len(frameworks)


async def create_compliance_snapshot(
    db: AsyncSession,
    user: User,
    *,
    notes: str = "",
) -> ComplianceSnapshot:
    frameworks, period_start, period_end, overall, compliant, total = await _load_compliance_metrics(db, user.tenant_id)
    snapshot = ComplianceSnapshot(
        tenant_id=user.tenant_id,
        created_by_id=user.id,
        created_by_name=user.name,
        period_start=period_start,
        period_end=period_end,
        overall_score=overall,
        frameworks_compliant=compliant,
        frameworks_total=total,
        notes=notes.strip(),
        frameworks=[f.model_dump() for f in frameworks],
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def list_compliance_snapshots(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    limit: int = 20,
) -> list[ComplianceSnapshot]:
    result = await db.execute(
        select(ComplianceSnapshot)
        .where(ComplianceSnapshot.tenant_id == tenant_id)
        .order_by(ComplianceSnapshot.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_compliance_snapshot(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    snapshot_id: str,
) -> ComplianceSnapshot | None:
    try:
        snapshot_uuid = uuid.UUID(snapshot_id)
    except ValueError:
        return None
    result = await db.execute(
        select(ComplianceSnapshot).where(
            ComplianceSnapshot.id == snapshot_uuid,
            ComplianceSnapshot.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


def export_snapshot_csv(snapshot: ComplianceSnapshot) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Framework",
            "Control ID",
            "Title",
            "Status",
            "Requirement",
            "Evidence",
            "Remediation",
            "HelixGuard Module",
        ]
    )
    for raw_framework in snapshot.frameworks or []:
        framework_name = raw_framework.get("name", "")
        for control in raw_framework.get("control_items") or []:
            writer.writerow(
                [
                    framework_name,
                    control.get("id", ""),
                    control.get("title", ""),
                    control.get("status", ""),
                    control.get("requirement", ""),
                    control.get("evidence") or "",
                    control.get("remediation") or "",
                    control.get("helixguard_module") or "",
                ]
            )
    return buffer.getvalue()


def export_snapshot_json(snapshot: ComplianceSnapshot) -> str:
    payload = {
        "id": str(snapshot.id),
        "created_at": snapshot.created_at.isoformat(),
        "created_by": snapshot.created_by_name,
        "period_start": snapshot.period_start.isoformat(),
        "period_end": snapshot.period_end.isoformat(),
        "overall_score": snapshot.overall_score,
        "frameworks_compliant": snapshot.frameworks_compliant,
        "frameworks_total": snapshot.frameworks_total,
        "notes": snapshot.notes,
        "frameworks": snapshot.frameworks,
    }
    return json.dumps(payload, indent=2)


async def load_live_frameworks(db: AsyncSession, tenant_id: uuid.UUID) -> list[DashboardComplianceFramework]:
    frameworks, *_ = await _load_compliance_metrics(db, tenant_id)
    return frameworks
