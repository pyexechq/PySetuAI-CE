"""Conditional RAG orchestrator — every hop must pass DLP + OPA before vector writes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.data_movement_service import DataMovementResult, evaluate_content_movement
from app.services.dlp_service import DlpScanResult, scan_content
from app.services.embedding_service import EmbeddingResult, embed_text
from app.services.integration_service import resolve_gateway_config
from app.services.pinecone_adapter import VectorStoreConfig, VectorUpsertResult, resolve_vector_store_config, upsert_vector


@dataclass
class RagPipelineHop:
    hop: str
    movement_from: str
    movement_to: str
    operation: str
    allowed: bool
    blocked_locally: bool = False
    detail: str | None = None


@dataclass
class ConditionalRagResult:
    allowed: bool
    hops: list[RagPipelineHop] = field(default_factory=list)
    dlp: DlpScanResult | None = None
    embedding: EmbeddingResult | None = None
    upsert: VectorUpsertResult | None = None
    vector_id: str | None = None
    destination: str = "pinecone"
    blocked_hop: str | None = None


def _hop_from_movement(name: str, movement: DataMovementResult) -> RagPipelineHop:
    return RagPipelineHop(
        hop=name,
        movement_from=movement.movement["from"],
        movement_to=movement.movement["to"],
        operation=movement.movement["operation"],
        allowed=movement.allowed,
        blocked_locally=movement.blocked_locally,
    )


async def run_conditional_rag_pipeline(
    content: str,
    *,
    db: AsyncSession,
    tenant_id: UUID,
    destination: str = "pinecone",
    region: str = "US",
    bundle_name: str | None = None,
    role: str = "client_key",
    auth_type: str = "jwt",
    document_id: str | None = None,
    namespace: str | None = None,
    exemption_id: str | None = None,
) -> ConditionalRagResult:
    tenant_key = str(tenant_id)
    dlp = scan_content(content, region=region)
    hops: list[RagPipelineHop] = []
    vector_id = document_id or str(uuid4())

    embed_movement = await evaluate_content_movement(
        content,
        db=db,
        tenant_uuid=tenant_id,
        destination="embedding",
        operation="embed",
        movement_from="document",
        region=region,
        tenant_id=tenant_key,
        bundle_name=bundle_name,
        role=role,
        auth_type=auth_type,
        exemption_id=exemption_id,
    )
    embed_hop = _hop_from_movement("document_to_embedding", embed_movement)
    hops.append(embed_hop)
    if not embed_movement.allowed:
        return ConditionalRagResult(
            allowed=False,
            hops=hops,
            dlp=dlp,
            destination=destination,
            blocked_hop=embed_hop.hop,
        )

    vector_destination = destination if destination in {"pinecone", "vector_store"} else "vector_store"
    upsert_movement = await evaluate_content_movement(
        content,
        db=db,
        tenant_uuid=tenant_id,
        destination=vector_destination,
        operation="upsert",
        movement_from="embedding",
        region=region,
        tenant_id=tenant_key,
        bundle_name=bundle_name,
        role=role,
        auth_type=auth_type,
        exemption_id=exemption_id,
    )
    upsert_hop = _hop_from_movement("embedding_to_vector_store", upsert_movement)
    hops.append(upsert_hop)
    if not upsert_movement.allowed:
        return ConditionalRagResult(
            allowed=False,
            hops=hops,
            dlp=dlp,
            destination=vector_destination,
            blocked_hop=upsert_hop.hop,
        )

    gateway = await resolve_gateway_config(db, tenant_id)
    vector_config: VectorStoreConfig = await resolve_vector_store_config(db, tenant_id)
    embedding = await embed_text(
        content,
        api_key=gateway.openai_api_key,
        dimensions=vector_config.dimension,
    )
    metadata: dict[str, Any] = {
        "highest_sensitivity": dlp.highest_sensitivity or "PUBLIC",
        "sensitivity_labels": dlp.sensitivity_labels,
        "classifications": dlp.classifications,
    }
    upsert = await upsert_vector(
        vector_config,
        vector_id=vector_id,
        values=embedding.vector,
        metadata=metadata,
        namespace=namespace,
    )

    if upsert.upserted and exemption_id and (embed_movement.exemption_applied or upsert_movement.exemption_applied):
        from app.services.policy_exemption_service import consume_policy_exemption, get_policy_exemption

        row = await get_policy_exemption(db, tenant_id, exemption_id)
        if row is not None:
            await consume_policy_exemption(db, row)

    return ConditionalRagResult(
        allowed=upsert.upserted,
        hops=hops,
        dlp=dlp,
        embedding=embedding,
        upsert=upsert,
        vector_id=vector_id,
        destination=vector_destination,
        blocked_hop=None if upsert.upserted else "vector_upsert",
    )
