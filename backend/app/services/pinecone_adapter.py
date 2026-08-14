"""Pinecone vector store adapter for governed RAG upserts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.governance import TenantIntegration
from app.services.integration_service import mask_secret


@dataclass
class VectorStoreConfig:
    enabled: bool
    api_key: str | None
    host: str | None
    namespace: str
    dimension: int
    source: str
    api_key_masked: str | None = None


@dataclass
class VectorUpsertResult:
    upserted: bool
    vector_id: str
    count: int = 0
    mock: bool = False
    error: str | None = None


async def resolve_vector_store_config(db: AsyncSession, tenant_id: UUID) -> VectorStoreConfig:
    result = await db.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id))
    row = result.scalar_one_or_none()

    enabled = settings.pinecone_enabled
    api_key = settings.pinecone_api_key
    host = settings.pinecone_host
    namespace = settings.pinecone_namespace
    dimension = settings.pinecone_dimension
    source = "environment"

    if row:
        if row.pinecone_enabled:
            enabled = True
            source = "tenant_settings"
        if row.pinecone_api_key:
            api_key = row.pinecone_api_key
            source = "tenant_settings"
        if row.pinecone_host:
            host = row.pinecone_host
            source = "tenant_settings" if source == "environment" else source
        if row.pinecone_namespace:
            namespace = row.pinecone_namespace
        if row.pinecone_dimension:
            dimension = row.pinecone_dimension

    return VectorStoreConfig(
        enabled=enabled,
        api_key=api_key,
        host=host.rstrip("/") if host else None,
        namespace=namespace,
        dimension=dimension,
        source=source,
        api_key_masked=mask_secret(api_key),
    )


async def upsert_vector(
    config: VectorStoreConfig,
    *,
    vector_id: str,
    values: list[float],
    metadata: dict[str, Any] | None = None,
    namespace: str | None = None,
) -> VectorUpsertResult:
    target_namespace = namespace if namespace is not None else config.namespace
    if not config.enabled or not config.api_key or not config.host:
        return VectorUpsertResult(
            upserted=False,
            vector_id=vector_id,
            mock=True,
            error="Pinecone is not configured — enable it in tenant integrations or environment.",
        )

    payload = {
        "vectors": [
            {
                "id": vector_id,
                "values": values,
                "metadata": metadata or {},
            }
        ],
    }
    if target_namespace:
        payload["namespace"] = target_namespace

    url = f"{config.host}/vectors/upsert"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={"Api-Key": config.api_key, "Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        return VectorUpsertResult(
            upserted=False,
            vector_id=vector_id,
            error=str(exc),
        )

    return VectorUpsertResult(
        upserted=True,
        vector_id=vector_id,
        count=int(body.get("upsertedCount", 1)),
        mock=False,
    )
