"""Auditor-ready evidence bundles for governed GenAI data movement."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import GenaiEvidenceBundle
from app.services.conditional_rag_service import ConditionalRagResult
from app.services.data_movement_service import DataMovementResult
from app.services.opa_service import OpaDecision

CONTROL_MAPPINGS: dict[str, list[str]] = {
    "RESTRICTED_PII": ["ISO 27001 A.8.11", "ISO 27701 7.4.7", "HIPAA §164.514"],
    "RESTRICTED_PHI": ["HIPAA §164.502", "ISO 27701 7.4.7"],
    "RESTRICTED_PCI": ["PCI DSS 3.4", "ISO 27001 A.8.11"],
    "CONFIDENTIAL_FINANCIAL": ["ISO 27001 A.8.11", "SOC 2 CC6.1"],
}


def _control_refs_for_labels(labels: list[str]) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for label in labels:
        for ref in CONTROL_MAPPINGS.get(label, []):
            if ref not in seen:
                seen.add(ref)
                refs.append(ref)
    return refs


def build_evidence_bundle(
    *,
    movement_result: DataMovementResult,
    tenant_id: str | None = None,
    actor: str | None = None,
    audit_event_id: str | None = None,
) -> dict[str, Any]:
    dlp = movement_result.dlp
    opa: OpaDecision = movement_result.opa
    return {
        "id": str(uuid4()),
        "generated_at": datetime.now(UTC).isoformat(),
        "tenant_id": tenant_id,
        "actor": actor,
        "audit_event_id": audit_event_id,
        "classification": {
            "entities": dlp.classifications,
            "sensitivity_labels": dlp.sensitivity_labels,
            "highest_sensitivity": dlp.highest_sensitivity,
            "match_count": dlp.match_count,
            "region": dlp.region,
        },
        "movement": movement_result.movement,
        "policy": {
            "engine": "opa",
            "allowed": movement_result.allowed,
            "blocked_locally": movement_result.blocked_locally,
            "skipped": opa.skipped,
            "available": opa.available,
            "violations": [
                {"rule": v.rule, "message": v.message, "severity": v.severity}
                for v in opa.violations
            ],
        },
        "control_mappings": _control_refs_for_labels(dlp.sensitivity_labels),
    }


def build_rag_pipeline_evidence_bundle(
    *,
    pipeline: ConditionalRagResult,
    tenant_id: str | None = None,
    actor: str | None = None,
) -> dict[str, Any]:
    dlp = pipeline.dlp
    labels = dlp.sensitivity_labels if dlp else []
    return {
        "id": str(uuid4()),
        "generated_at": datetime.now(UTC).isoformat(),
        "tenant_id": tenant_id,
        "actor": actor,
        "bundle_type": "conditional_rag",
        "classification": {
            "entities": dlp.classifications if dlp else [],
            "sensitivity_labels": labels,
            "highest_sensitivity": dlp.highest_sensitivity if dlp else None,
            "match_count": dlp.match_count if dlp else 0,
            "region": dlp.region if dlp else "US",
        },
        "pipeline": {
            "allowed": pipeline.allowed,
            "blocked_hop": pipeline.blocked_hop,
            "destination": pipeline.destination,
            "vector_id": pipeline.vector_id,
            "hops": [
                {
                    "hop": hop.hop,
                    "from": hop.movement_from,
                    "to": hop.movement_to,
                    "operation": hop.operation,
                    "allowed": hop.allowed,
                    "blocked_locally": hop.blocked_locally,
                }
                for hop in pipeline.hops
            ],
        },
        "embedding": (
            {
                "model": pipeline.embedding.model,
                "source": pipeline.embedding.source,
                "dimensions": pipeline.embedding.dimensions,
            }
            if pipeline.embedding
            else None
        ),
        "upsert": (
            {
                "upserted": pipeline.upsert.upserted,
                "vector_id": pipeline.upsert.vector_id,
                "count": pipeline.upsert.count,
                "mock": pipeline.upsert.mock,
                "error": pipeline.upsert.error,
            }
            if pipeline.upsert
            else None
        ),
        "control_mappings": _control_refs_for_labels(labels),
    }


async def save_evidence_bundle(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    actor: str,
    payload: dict[str, Any],
) -> GenaiEvidenceBundle:
    row = GenaiEvidenceBundle(
        id=UUID(payload["id"]),
        tenant_id=tenant_id,
        actor=actor,
        payload=payload,
    )
    db.add(row)
    await db.flush()
    return row


async def list_evidence_bundles(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    limit: int = 50,
) -> list[GenaiEvidenceBundle]:
    result = await db.execute(
        select(GenaiEvidenceBundle)
        .where(GenaiEvidenceBundle.tenant_id == tenant_id)
        .order_by(GenaiEvidenceBundle.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_evidence_bundle(
    db: AsyncSession,
    tenant_id: UUID,
    bundle_id: str,
) -> GenaiEvidenceBundle | None:
    try:
        bundle_uuid = UUID(bundle_id)
    except ValueError:
        return None
    result = await db.execute(
        select(GenaiEvidenceBundle).where(
            GenaiEvidenceBundle.id == bundle_uuid,
            GenaiEvidenceBundle.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()
