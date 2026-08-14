"""UAG admin operations and statistics."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import TenantIntegration
from app.models.uag import UagModelMapping, UagTranslationEvent, UagTranslationPolicy
from app.modules.uag.client_response import normalize_client_protocol
from app.modules.uag.provider_registry import DEFAULT_COMPATIBILITY_SCORES


def mapping_to_dict(row: UagModelMapping) -> dict:
    return {
        "id": str(row.id),
        "requested_model": row.requested_model,
        "actual_model": row.actual_model,
        "target_provider": row.target_provider,
        "emulate_protocol": row.emulate_protocol,
        "enabled": row.enabled,
    }


def policy_to_dict(row: UagTranslationPolicy) -> dict:
    return {
        "id": str(row.id),
        "name": row.name,
        "conditions": row.conditions or {},
        "actions": row.actions or {},
        "priority": row.priority,
        "enabled": row.enabled,
    }


async def get_uag_settings(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    result = await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id))
    row = result.scalar_one_or_none()
    if row is None:
        return {"client_response_protocol": "openai"}
    return {
        "client_response_protocol": normalize_client_protocol(row.uag_client_protocol or "openai"),
    }


async def update_uag_settings(db: AsyncSession, tenant_id: uuid.UUID, data: dict) -> dict:
    result = await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id))
    row = result.scalar_one_or_none()
    if row is None:
        row = TenantIntegration(tenant_id=tenant_id)
        db.add(row)

    if "client_response_protocol" in data and data["client_response_protocol"] is not None:
        row.uag_client_protocol = normalize_client_protocol(str(data["client_response_protocol"]))

    await db.commit()
    await db.refresh(row)
    return await get_uag_settings(db, tenant_id)


async def list_mappings(db: AsyncSession, tenant_id: uuid.UUID) -> list[UagModelMapping]:
    result = await db.execute(
        select(UagModelMapping)
        .where(UagModelMapping.tenant_id == tenant_id)
        .order_by(UagModelMapping.requested_model.asc())
    )
    return list(result.scalars().all())


async def create_mapping(db: AsyncSession, tenant_id: uuid.UUID, data: dict) -> UagModelMapping:
    from app.services.registry_alias_service import sync_alias_to_registry

    row = UagModelMapping(
        tenant_id=tenant_id,
        requested_model=data["requested_model"].strip(),
        actual_model=data["actual_model"].strip(),
        target_provider=data.get("target_provider", "openai").strip(),
        emulate_protocol=normalize_client_protocol(data.get("emulate_protocol", "openai")),
        enabled=bool(data.get("enabled", True)),
    )
    db.add(row)
    await sync_alias_to_registry(
        db,
        tenant_id,
        requested_model=row.requested_model,
        actual_model=row.actual_model,
        provider_type=row.target_provider,
    )
    await db.commit()
    await db.refresh(row)
    return row


async def update_mapping(db: AsyncSession, row: UagModelMapping, data: dict) -> UagModelMapping:
    from app.services.registry_alias_service import sync_alias_to_registry

    for field in ("requested_model", "actual_model", "target_provider", "emulate_protocol"):
        if field in data and data[field] is not None:
            setattr(row, field, str(data[field]).strip())
    if "enabled" in data and data["enabled"] is not None:
        row.enabled = bool(data["enabled"])
    if row.enabled:
        await sync_alias_to_registry(
            db,
            row.tenant_id,
            requested_model=row.requested_model,
            actual_model=row.actual_model,
            provider_type=row.target_provider,
        )
    await db.commit()
    await db.refresh(row)
    return row


async def delete_mapping(db: AsyncSession, row: UagModelMapping) -> None:
    await db.delete(row)
    await db.commit()


async def get_mapping(db: AsyncSession, tenant_id: uuid.UUID, mapping_id: uuid.UUID) -> UagModelMapping | None:
    result = await db.execute(
        select(UagModelMapping).where(
            UagModelMapping.tenant_id == tenant_id,
            UagModelMapping.id == mapping_id,
        )
    )
    return result.scalar_one_or_none()


async def list_policies(db: AsyncSession, tenant_id: uuid.UUID) -> list[UagTranslationPolicy]:
    result = await db.execute(
        select(UagTranslationPolicy)
        .where(UagTranslationPolicy.tenant_id == tenant_id)
        .order_by(UagTranslationPolicy.priority.asc())
    )
    return list(result.scalars().all())


async def create_policy(db: AsyncSession, tenant_id: uuid.UUID, data: dict) -> UagTranslationPolicy:
    row = UagTranslationPolicy(
        tenant_id=tenant_id,
        name=data["name"].strip(),
        conditions=data.get("conditions") or {},
        actions=data.get("actions") or {},
        priority=int(data.get("priority", 100)),
        enabled=bool(data.get("enabled", True)),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def update_policy(db: AsyncSession, row: UagTranslationPolicy, data: dict) -> UagTranslationPolicy:
    if "name" in data and data["name"] is not None:
        row.name = str(data["name"]).strip()
    if "conditions" in data and data["conditions"] is not None:
        row.conditions = data["conditions"]
    if "actions" in data and data["actions"] is not None:
        row.actions = data["actions"]
    if "priority" in data and data["priority"] is not None:
        row.priority = int(data["priority"])
    if "enabled" in data and data["enabled"] is not None:
        row.enabled = bool(data["enabled"])
    await db.commit()
    await db.refresh(row)
    return row


async def delete_policy(db: AsyncSession, row: UagTranslationPolicy) -> None:
    await db.delete(row)
    await db.commit()


async def get_policy(db: AsyncSession, tenant_id: uuid.UUID, policy_id: uuid.UUID) -> UagTranslationPolicy | None:
    result = await db.execute(
        select(UagTranslationPolicy).where(
            UagTranslationPolicy.tenant_id == tenant_id,
            UagTranslationPolicy.id == policy_id,
        )
    )
    return result.scalar_one_or_none()


async def record_translation_event(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    request_id: str,
    source_protocol: str,
    target_provider: str,
    requested_model: str,
    translated_model: str,
    success: bool,
    latency_ms: float,
    compatibility_score: float | None,
    details: str = "",
) -> None:
    db.add(
        UagTranslationEvent(
            tenant_id=tenant_id,
            request_id=request_id,
            source_protocol=source_protocol,
            target_provider=target_provider,
            requested_model=requested_model,
            translated_model=translated_model,
            success=success,
            latency_ms=latency_ms,
            compatibility_score=compatibility_score,
            details=details,
        )
    )


async def build_stats(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    since = datetime.now(UTC) - timedelta(days=30)
    filters = (
        UagTranslationEvent.tenant_id == tenant_id,
        UagTranslationEvent.created_at >= since,
    )

    total_result = await db.execute(select(func.count(UagTranslationEvent.id)).where(*filters))
    total = total_result.scalar() or 0

    success_result = await db.execute(
        select(func.count(UagTranslationEvent.id)).where(*filters, UagTranslationEvent.success.is_(True))
    )
    success = success_result.scalar() or 0
    failed = total - success

    latency_result = await db.execute(select(func.avg(UagTranslationEvent.latency_ms)).where(*filters))
    avg_latency = float(latency_result.scalar() or 0.0)

    route_result = await db.execute(
        select(UagTranslationEvent.source_protocol, UagTranslationEvent.target_provider, func.count(UagTranslationEvent.id))
        .where(*filters)
        .group_by(UagTranslationEvent.source_protocol, UagTranslationEvent.target_provider)
    )
    route_breakdown = {f"{src} → {tgt}": count for src, tgt, count in route_result.all()}

    compatibility_scores = {
        f"{src} → {tgt}": score for (src, tgt), score in DEFAULT_COMPATIBILITY_SCORES.items()
    }

    return {
        "total_translations": total,
        "success_rate": (success / total) if total else 1.0,
        "failed_translations": failed,
        "avg_latency_ms": avg_latency,
        "compatibility_scores": compatibility_scores,
        "route_breakdown": route_breakdown,
    }
