"""Scheduled LLM provider percentage rebalancing."""

from __future__ import annotations

import logging

from app.db import async_session_factory
from app.services.provider_metrics_service import rebalance_all_tenants

logger = logging.getLogger(__name__)


async def run_scheduled_provider_rebalance() -> dict:
    async with async_session_factory() as db:
        summary = await rebalance_all_tenants(db)
    if summary["providers_updated"]:
        logger.info(
            "Rebalanced LLM routing shares for %s tenant(s), %s provider(s)",
            summary["tenants_updated"],
            summary["providers_updated"],
        )
    return summary
