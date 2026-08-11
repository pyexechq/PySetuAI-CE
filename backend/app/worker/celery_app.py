from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "pysetu",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

beat_schedule = {
    "process-due-scheduled-reports": {
        "task": "app.worker.tasks.process_due_scheduled_reports",
        "schedule": 60.0,
    },
    "export-siem-connectors": {
        "task": "app.worker.tasks.export_siem_connectors",
        "schedule": 300.0,
    },
}

if settings.llm_rebalance_schedule_enabled:
    beat_schedule["rebalance-llm-provider-percentages"] = {
        "task": "app.worker.tasks.rebalance_all_tenant_llm_providers",
        "schedule": crontab(
            hour=settings.llm_rebalance_cron_hour,
            minute=settings.llm_rebalance_cron_minute,
        ),
    }

celery_app.conf.beat_schedule = beat_schedule
