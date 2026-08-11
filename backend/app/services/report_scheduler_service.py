import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.db import async_session_factory
from app.models.governance import ReportDefinition
from app.services.report_email_service import send_report_email
from app.services.report_export_service import build_report_download
from app.services.report_service import get_report_by_id, report_public_id, run_report
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


async def enqueue_due_reports() -> int:
    now = datetime.now(UTC)
    async with async_session_factory() as db:
        result = await db.execute(
            select(ReportDefinition).where(
                ReportDefinition.schedule_enabled.is_(True),
                ReportDefinition.generation_status != "generating",
                ReportDefinition.next_run_at.is_not(None),
                ReportDefinition.next_run_at <= now,
            )
        )
        due = list(result.scalars().all())
        if not due:
            return 0

        for report in due:
            report.generation_status = "generating"
        await db.commit()

    for report in due:
        celery_app.send_task(
            "app.worker.tasks.run_scheduled_report",
            args=[str(report.id), str(report.tenant_id)],
        )
        logger.info(
            "Queued scheduled report %s for tenant %s",
            report_public_id(report),
            report.tenant_id,
        )

    return len(due)


async def generate_and_deliver_report(report_id: UUID, tenant_id: UUID) -> dict:
    try:
        async with async_session_factory() as db:
            report = await get_report_by_id(db, tenant_id, str(report_id))
            if report is None:
                return {"status": "not_found"}

            result = await run_report(db, report)
            content, media_type, filename = build_report_download(
                report_name=report.name,
                category=report.category,
                report_format=report.format,
                run_result=result,
            )
            delivery = send_report_email(
                recipients=report.schedule_recipients or [],
                report_name=report.name,
                attachment_bytes=content,
                attachment_filename=filename,
                attachment_mime=media_type,
                row_count=int(result.get("row_count") or 0),
            )
            result["delivery"] = delivery

            refreshed = await get_report_by_id(db, tenant_id, str(report_id))
            if refreshed is not None:
                refreshed.last_run_result = result
                await db.commit()

            return {
                "status": "completed",
                "report_id": report_public_id(report),
                "delivery": delivery,
            }
    except Exception:
        async with async_session_factory() as err_db:
            failed = await get_report_by_id(err_db, tenant_id, str(report_id))
            if failed is not None:
                failed.generation_status = "error"
                await err_db.commit()
        raise
