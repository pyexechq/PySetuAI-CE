import asyncio
import logging
from uuid import UUID

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_with_clean_engine(coro):
    """Dispose the async engine after each Celery task to avoid asyncpg loop conflicts."""
    from app.db import engine

    try:
        return await coro
    finally:
        await engine.dispose()


def _run_async(coro):
    return asyncio.run(_run_with_clean_engine(coro))


@celery_app.task(name="app.worker.tasks.process_due_scheduled_reports")
def process_due_scheduled_reports() -> int:
    from app.services.report_scheduler_service import enqueue_due_reports

    count = _run_async(enqueue_due_reports())
    if count:
        logger.info("Enqueued %s scheduled report job(s)", count)
    return count


@celery_app.task(name="app.worker.tasks.rebalance_all_tenant_llm_providers")
def rebalance_all_tenant_llm_providers() -> dict:
    from app.services.provider_rebalance_service import run_scheduled_provider_rebalance

    return _run_async(run_scheduled_provider_rebalance())


@celery_app.task(name="app.worker.tasks.ingest_audit_batch", bind=True, max_retries=2)
def ingest_audit_batch(self, tenant_id: str, events: list[dict]) -> dict:
    from app.services.audit_ingestion_service import ingest_audit_events

    async def _run():
        from app.db import async_session_factory

        async with async_session_factory() as db:
            return await ingest_audit_events(db, UUID(tenant_id), events)

    try:
        result = _run_async(_run())
        return {
            "accepted": result.accepted,
            "skipped": result.skipped,
            "duplicates": result.duplicates,
            "ids": result.ids,
        }
    except Exception as exc:
        logger.exception("Audit ingest batch failed tenant_id=%s", tenant_id)
        raise self.retry(exc=exc, countdown=15) from exc


@celery_app.task(name="app.worker.tasks.export_siem_connectors", bind=True, max_retries=2)
def export_siem_connectors(self, tenant_id: str | None = None) -> dict:
    from app.services.siem_connector_service import export_all_enabled_connectors, list_connectors, run_connector_export

    async def _run():
        from uuid import UUID

        from app.db import async_session_factory

        async with async_session_factory() as db:
            if tenant_id:
                connectors = await list_connectors(db, UUID(tenant_id))
                results = []
                for connector in connectors:
                    if not connector.enabled:
                        continue
                    try:
                        outcome = await run_connector_export(db, UUID(tenant_id), connector)
                        results.append(outcome.__dict__)
                    except Exception as exc:
                        results.append({"connector_id": str(connector.id), "error": str(exc)})
                return {"connectors": len(connectors), "results": results}
            outcomes = await export_all_enabled_connectors(db)
            return {"connectors": len(outcomes), "results": [o.__dict__ for o in outcomes]}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.exception("SIEM export failed tenant_id=%s", tenant_id)
        raise self.retry(exc=exc, countdown=30) from exc


@celery_app.task(name="app.worker.tasks.run_scheduled_report", bind=True, max_retries=2)
def run_scheduled_report(self, report_id: str, tenant_id: str) -> dict:
    from app.services.report_scheduler_service import generate_and_deliver_report

    try:
        return _run_async(generate_and_deliver_report(UUID(report_id), UUID(tenant_id)))
    except Exception as exc:
        logger.exception("Scheduled report failed report_id=%s", report_id)
        raise self.retry(exc=exc, countdown=30) from exc


@celery_app.task(name="app.worker.tasks.run_guardian_loop_all_tenants", bind=True, max_retries=2)
def run_guardian_loop_all_tenants(self) -> dict:
    """Run the Guardian enforcement loop for every active tenant."""
    from sqlalchemy import select

    from app.db import async_session_factory
    from app.models.tenant import Tenant
    from app.services.guardian_service import run_guardian_loop

    async def _run():
        async with async_session_factory() as db:
            tenant_result = await db.execute(
                select(Tenant).where(Tenant.is_active.is_(True))
            )
            tenants = tenant_result.scalars().all()
            per_tenant = []
            for tenant in tenants:
                try:
                    outcome = await run_guardian_loop(db, tenant.id)
                    await db.commit()
                    per_tenant.append(
                        {
                            "tenant_id": str(tenant.id),
                            "evaluated": outcome["evaluated"],
                            "executed": outcome["executed"],
                            "failed": outcome["failed"],
                        }
                    )
                except Exception as exc:
                    await db.rollback()
                    logger.exception("Guardian loop failed tenant_id=%s", tenant.id)
                    per_tenant.append(
                        {"tenant_id": str(tenant.id), "error": str(exc)}
                    )
            return {"tenants": len(tenants), "results": per_tenant}

    try:
        return _run_async(_run())
    except Exception as exc:
        logger.exception("Guardian loop all-tenants run failed")
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(name="app.worker.tasks.run_nightly_classifier_benchmark")
def run_nightly_classifier_benchmark() -> dict:
    """Execute nightly regression benchmark against the golden 10,000 dataset."""
    from app.services.classifier.evaluator import execute_dataset_benchmark

    async def _run():
        result = await execute_dataset_benchmark(sample_limit=10000)
        logger.info(
            "Nightly Classifier Benchmark: Accuracy=%.2f%%, Recall=%.2f%%, Latency=%.1fμs",
            result["accuracy_percent"],
            result["recall_percent"],
            result["latency_profile"]["avg_micros"],
        )
        return {
            "accuracy_percent": result["accuracy_percent"],
            "recall_percent": result["recall_percent"],
            "f1_score_percent": result["f1_score_percent"],
            "avg_latency_micros": result["latency_profile"]["avg_micros"],
            "total_rows": result["total_rows"],
        }

    return _run_async(_run())
