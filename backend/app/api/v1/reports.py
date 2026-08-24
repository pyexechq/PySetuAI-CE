from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.date_range import parse_date_range
from app.core.deps import require_reports
from app.core.rbac import VIEW_COMPLIANCE, require_permission, require_roles
from app.db.session import get_db
from app.models.governance import AuditLog, ReportDefinition
from app.models.tenant import User
from app.schemas.reports import (
    CompoundingCostSummary,
    ExecutiveSummaryResponse,
    ReportCatalogItem,
    ReportCatalogResponse,
    ReportCreateRequest,
    ReportDeliveryRecipient,
    ReportDeliveryRecipientsResponse,
    ReportKpiResponse,
    ReportPreviewRequest,
    ReportPreviewResponse,
    ReportQueryTemplate,
    ReportQueryTemplateField,
    ReportQueryTemplatesResponse,
    ReportRunResponse,
    ReportSchedule,
    ReportSchedulerStatus,
    ReportUpdateRequest,
)
from app.services.compliance_service import GATED_AUDIT_STATUSES, build_compliance_frameworks, overall_compliance_score
from app.services.compounding_cost_service import summarize_compounding_savings
from app.services.report_export_service import build_report_download
from app.services.report_service import (
    QUERY_TEMPLATES,
    catalog_item_dict,
    compute_next_run,
    ensure_tenant_reports,
    execute_report_generation,
    execute_report_query,
    get_report_by_id,
    report_public_id,
)

router = APIRouter(dependencies=[Depends(require_reports)])

_require_compliance = require_permission(VIEW_COMPLIANCE)
_require_report_admin = require_roles("tenant_admin", "platform_admin")


def _apply_schedule(report: ReportDefinition, schedule: ReportSchedule) -> None:
    if schedule.enabled and schedule.frequency != "on_demand" and not schedule.recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one delivery recipient is required when scheduling is enabled.",
        )
    report.schedule_enabled = schedule.enabled
    report.schedule_frequency = schedule.frequency
    report.schedule_time = schedule.time
    report.schedule_day_of_week = schedule.day_of_week
    report.schedule_day_of_month = schedule.day_of_month
    report.schedule_recipients = schedule.recipients
    report.next_run_at = compute_next_run(report)


@router.get("/reports/executive-summary", response_model=ExecutiveSummaryResponse)
async def executive_summary(
    current_user: Annotated[User, Depends(_require_compliance)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: str | None = Query(None),
    to_date: str | None = Query(None),
) -> ExecutiveSummaryResponse:
    tenant_id = current_user.tenant_id
    range_start, range_end = parse_date_range(from_date, to_date)
    if range_start is None and range_end is None:
        now = datetime.now(UTC)
        range_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        range_end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        period_label = now.strftime("%B %Y")
    else:
        if range_start is None:
            range_start = (range_end or datetime.now(UTC)) - timedelta(days=30)
        if range_end is None:
            range_end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        period_label = f"{range_start.strftime('%b %d')} – {(range_end - timedelta(days=1)).strftime('%b %d, %Y')}"

    base = AuditLog.tenant_id == tenant_id
    range_filter = (AuditLog.timestamp >= range_start, AuditLog.timestamp < range_end)
    # Only count requests the DLP/policy engine actually decisioned; excludes discovery,
    # heartbeat, and other non-gated telemetry rows that would dilute the metrics below.
    gated = AuditLog.status.in_(GATED_AUDIT_STATUSES)

    total = await db.execute(select(func.count(AuditLog.id)).where(base, *range_filter, gated))
    blocked = await db.execute(select(func.count(AuditLog.id)).where(base, *range_filter, gated, AuditLog.status == "blocked"))
    allowed = await db.execute(select(func.count(AuditLog.id)).where(base, *range_filter, gated, AuditLog.status == "allowed"))
    high_risk = await db.execute(select(func.count(AuditLog.id)).where(base, *range_filter, gated, AuditLog.risk == "high"))

    total_n = total.scalar() or 0
    blocked_n = blocked.scalar() or 0
    allowed_n = allowed.scalar() or 0
    high_risk_n = high_risk.scalar() or 0

    block_rate = round((blocked_n / total_n * 100) if total_n else 0.0, 1)
    compliance_score = max(
        0.0,
        min(100.0, round(100 - (blocked_n / total_n * 100) if total_n else 92.0, 1)),
    )
    pii_result = await db.execute(
        select(func.count(AuditLog.id)).where(base, *range_filter, gated, AuditLog.action.ilike("%PII%"))
    )
    pii_n = pii_result.scalar() or 0

    # Compute period-over-period change from the immediately preceding window.
    period_len = range_end - range_start
    prev_start = range_start - period_len
    prev_filter = (AuditLog.timestamp >= prev_start, AuditLog.timestamp < range_start)
    prev_total = (await db.execute(select(func.count(AuditLog.id)).where(base, *prev_filter, gated))).scalar() or 0
    prev_blocked = (
        await db.execute(select(func.count(AuditLog.id)).where(base, *prev_filter, gated, AuditLog.status == "blocked"))
    ).scalar() or 0
    prev_allowed = (
        await db.execute(select(func.count(AuditLog.id)).where(base, *prev_filter, gated, AuditLog.status == "allowed"))
    ).scalar() or 0
    prev_high_risk = (
        await db.execute(select(func.count(AuditLog.id)).where(base, *prev_filter, gated, AuditLog.risk == "high"))
    ).scalar() or 0

    def _pct(current: int, previous: int) -> float:
        if previous <= 0:
            return 0.0 if current <= 0 else 100.0
        return round(((current - previous) / previous) * 100, 1)

    total_change = _pct(total_n, prev_total)
    blocked_change = _pct(blocked_n, prev_blocked)
    allowed_change = _pct(allowed_n, prev_allowed)
    high_risk_change = _pct(high_risk_n, prev_high_risk)

    # Derive top risks from actual blocked events rather than a static list.
    top_risk_rows = await db.execute(
        select(AuditLog.details, func.count(AuditLog.id))
        .where(base, *range_filter, gated, AuditLog.status == "blocked")
        .group_by(AuditLog.details)
        .order_by(func.count(AuditLog.id).desc())
        .limit(3)
    )
    top_risks = [
        (row[0][:80] if row[0] else "Blocked request")
        for row in top_risk_rows.all()
    ]
    if not top_risks:
        top_risks = ["No blocked events in this period"]

    usage_rows = await db.execute(
        select(AuditLog.usage_metadata).where(base, *range_filter, gated, AuditLog.usage_metadata.is_not(None))
    )
    cost_optimization = CompoundingCostSummary(**summarize_compounding_savings([row[0] for row in usage_rows.all()]))

    frameworks = await build_compliance_frameworks(
        db,
        tenant_id,
        compliance_score=compliance_score,
        block_rate=block_rate,
        pii_events=pii_n,
        blocked_requests=blocked_n,
        total_requests=total_n,
        audit_start=range_start,
        audit_end=range_end,
    )
    avg_score = overall_compliance_score(frameworks) if frameworks else compliance_score
    frameworks_compliant = sum(1 for f in frameworks if f.status == "compliant")

    def _trend(value: float, *, invert: bool = False) -> str:
        good = value <= 0 if invert else value >= 0
        return "up" if value > 0 else "down" if value < 0 else "flat"

    return ExecutiveSummaryResponse(
        period=period_label,
        kpis=[
            ReportKpiResponse(
                label="AI Requests",
                value=f"{total_n:,}",
                change=f"{total_change:+.1f}%",
                trend=_trend(total_change),
            ),
            ReportKpiResponse(
                label="Policy Blocks",
                value=f"{blocked_n:,}",
                change=f"{blocked_change:+.1f}%",
                trend=_trend(blocked_change, invert=True),
            ),
            ReportKpiResponse(
                label="Allowed Actions",
                value=f"{allowed_n:,}",
                change=f"{allowed_change:+.1f}%",
                trend=_trend(allowed_change),
            ),
            ReportKpiResponse(
                label="High-Risk Events",
                value=f"{high_risk_n:,}",
                change=f"{high_risk_change:+.1f}%",
                trend=_trend(high_risk_change, invert=True),
            ),
            ReportKpiResponse(
                label="Stacked cost savings",
                value=f"${cost_optimization.total_estimated_usd:,.2f}",
                change=f"{cost_optimization.total_tokens_saved:,} tok",
                trend="down",
            ),
        ],
        compliance_score=avg_score,
        frameworks_compliant=frameworks_compliant,
        frameworks_total=len(frameworks) or 5,
        top_risks=top_risks,
        cost_optimization=cost_optimization,
    )


@router.get("/reports/query-templates", response_model=ReportQueryTemplatesResponse)
async def query_templates(
    _current_user: Annotated[User, Depends(_require_compliance)],
) -> ReportQueryTemplatesResponse:
    return ReportQueryTemplatesResponse(
        templates=[
            ReportQueryTemplate(
                source=t["source"],
                label=t["label"],
                description=t["description"],
                filter_fields=[ReportQueryTemplateField(**field) for field in t["filter_fields"]],
            )
            for t in QUERY_TEMPLATES
        ]
    )


@router.get("/reports/delivery-recipients", response_model=ReportDeliveryRecipientsResponse)
async def delivery_recipients(
    current_user: Annotated[User, Depends(_require_compliance)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportDeliveryRecipientsResponse:
    result = await db.execute(
        select(User.email, User.name, User.role).where(
            User.tenant_id == current_user.tenant_id,
            User.is_active.is_(True),
        )
    )
    rows = result.all()
    return ReportDeliveryRecipientsResponse(
        recipients=[ReportDeliveryRecipient(email=row[0], name=row[1], role=row[2]) for row in rows]
    )


@router.get("/reports/catalog", response_model=ReportCatalogResponse)
async def report_catalog(
    current_user: Annotated[User, Depends(_require_compliance)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportCatalogResponse:
    await ensure_tenant_reports(db, current_user.tenant_id)
    result = await db.execute(
        select(ReportDefinition)
        .where(ReportDefinition.tenant_id == current_user.tenant_id)
        .order_by(ReportDefinition.is_builtin.desc(), ReportDefinition.name)
    )
    reports = result.scalars().all()
    return ReportCatalogResponse(reports=[ReportCatalogItem(**catalog_item_dict(r)) for r in reports])


@router.post("/reports", response_model=ReportCatalogItem, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreateRequest,
    current_user: Annotated[User, Depends(_require_report_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportCatalogItem:
    report = ReportDefinition(
        tenant_id=current_user.tenant_id,
        name=payload.name.strip(),
        description=payload.description.strip(),
        category=payload.category.strip() or "Custom",
        format=payload.format.upper(),
        query=payload.query.model_dump(),
        is_builtin=False,
    )
    if payload.schedule:
        _apply_schedule(report, payload.schedule)
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return ReportCatalogItem(**catalog_item_dict(report))


@router.put("/reports/{report_id}", response_model=ReportCatalogItem)
async def update_report(
    report_id: str,
    payload: ReportUpdateRequest,
    current_user: Annotated[User, Depends(_require_report_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportCatalogItem:
    report = await get_report_by_id(db, current_user.tenant_id, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if payload.name is not None:
        report.name = payload.name.strip()
    if payload.description is not None:
        report.description = payload.description.strip()
    if payload.category is not None:
        report.category = payload.category.strip()
    if payload.format is not None:
        report.format = payload.format.upper()
    if payload.query is not None:
        report.query = payload.query.model_dump()
    if payload.schedule is not None:
        _apply_schedule(report, payload.schedule)

    await db.commit()
    await db.refresh(report)
    return ReportCatalogItem(**catalog_item_dict(report))


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    current_user: Annotated[User, Depends(_require_report_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    report = await get_report_by_id(db, current_user.tenant_id, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.is_builtin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Built-in reports cannot be deleted")
    await db.delete(report)
    await db.commit()


@router.post("/reports/{report_id}/preview", response_model=ReportPreviewResponse)
async def preview_report_by_id(
    report_id: str,
    current_user: Annotated[User, Depends(_require_compliance)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportPreviewResponse:
    report = await get_report_by_id(db, current_user.tenant_id, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    columns, rows = await execute_report_query(db, current_user.tenant_id, report.query)
    return ReportPreviewResponse(columns=columns, rows=rows[:50], row_count=len(rows))


@router.post("/reports/preview", response_model=ReportPreviewResponse)
async def preview_report_query(
    payload: ReportPreviewRequest,
    current_user: Annotated[User, Depends(_require_compliance)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportPreviewResponse:
    columns, rows = await execute_report_query(db, current_user.tenant_id, payload.query.model_dump())
    return ReportPreviewResponse(columns=columns, rows=rows[:20], row_count=len(rows))


@router.post("/reports/{report_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_report_endpoint(
    report_id: str,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(_require_compliance)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    report = await get_report_by_id(db, current_user.tenant_id, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.generation_status == "generating":
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"report_id": report_public_id(report), "status": "generating"},
        )

    report.generation_status = "generating"
    report.last_run_result = None
    await db.commit()

    background_tasks.add_task(execute_report_generation, report.id, current_user.tenant_id)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"report_id": report_public_id(report), "status": "generating"},
    )


@router.get("/reports/{report_id}/run", response_model=ReportRunResponse)
async def get_report_run_result(
    report_id: str,
    current_user: Annotated[User, Depends(_require_compliance)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportRunResponse | JSONResponse:
    report = await get_report_by_id(db, current_user.tenant_id, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if report.generation_status == "generating":
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"report_id": report_public_id(report), "status": "generating"},
        )

    if report.generation_status == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Report generation failed")

    if not report.last_run_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No report run result available")

    return ReportRunResponse(**report.last_run_result)


@router.get("/reports/{report_id}/download", response_model=None)
async def download_report(
    report_id: str,
    current_user: Annotated[User, Depends(_require_compliance)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response | JSONResponse:
    report = await get_report_by_id(db, current_user.tenant_id, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if report.generation_status == "generating":
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={"report_id": report_public_id(report), "status": "generating"},
        )

    if report.generation_status == "error":
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Report generation failed")

    if not report.last_run_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No report data available. Run the report first.",
        )

    content, media_type, filename = build_report_download(
        report_name=report.name,
        category=report.category,
        report_format=report.format,
        run_result=report.last_run_result,
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/scheduler/status", response_model=ReportSchedulerStatus)
async def report_scheduler_status(
    current_user: Annotated[User, Depends(_require_report_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReportSchedulerStatus:
    now = datetime.now(UTC)
    due = await db.execute(
        select(func.count(ReportDefinition.id)).where(
            ReportDefinition.tenant_id == current_user.tenant_id,
            ReportDefinition.schedule_enabled.is_(True),
            ReportDefinition.generation_status != "generating",
            ReportDefinition.next_run_at.is_not(None),
            ReportDefinition.next_run_at <= now,
        )
    )
    mailhog_ui = "http://localhost:8025" if settings.smtp_host == "mailhog" else None
    return ReportSchedulerStatus(
        celery_broker=settings.redis_url,
        smtp_enabled=settings.smtp_enabled,
        smtp_host=settings.smtp_host,
        due_reports=due.scalar() or 0,
        mailhog_ui=mailhog_ui,
    )


@router.get("/reports/scheduler/run-due", response_model=None)
async def report_scheduler_run_due_help(request: Request):
    """Browser GET lands here with 405 on POST-only routes; explain how to trigger schedules."""
    accept = request.headers.get("accept", "")
    payload = {
        "detail": "Method Not Allowed. Use POST with admin Bearer token, or the Reports page “Run due reports” button.",
        "post_url": f"{settings.api_prefix}/reports/scheduler/run-due",
        "status_url": f"{settings.api_prefix}/reports/scheduler/status",
        "ui": f"{settings.frontend_url}/reports",
    }
    if "text/html" in accept and "application/json" not in accept:
        return HTMLResponse(
            f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Report scheduler</title>
<style>body{{font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.5}}
code{{background:#f1f5f9;padding:.1rem .35rem;border-radius:4px}}</style></head>
<body><h1>Report scheduler — manual trigger</h1>
<p>This endpoint requires <strong>POST</strong> and an admin login token. Opening it in the browser sends GET, so nothing runs.</p>
<ul>
<li>Use the <a href="{payload["ui"]}">Reports</a> page → <strong>Run due reports</strong></li>
<li>Or POST to <code>{payload["post_url"]}</code> with <code>Authorization: Bearer …</code></li>
<li>Check status: <code>{payload["status_url"]}</code></li>
</ul>
<p>API base: port <strong>8001</strong> (not the Next.js UI on 3000 unless proxied via <code>/api/v1/…</code>).</p>
</body></html>"""
        )
    return JSONResponse(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, content=payload)


@router.post("/reports/scheduler/run-due")
async def trigger_due_reports(
    current_user: Annotated[User, Depends(_require_report_admin)],
) -> dict[str, int]:
    from app.worker.tasks import process_due_scheduled_reports

    try:
        enqueued = process_due_scheduled_reports.delay().get(timeout=30)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Celery worker unavailable: {exc}",
        ) from exc
    return {"enqueued": enqueued}
