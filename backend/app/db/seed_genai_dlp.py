"""Demo GenAI DLP audit events and evidence bundles for the Acme tenant."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.db import async_session_factory
from app.models.governance import AuditLog, GenaiEvidenceBundle, TenantIntegration
from app.models.tenant import Tenant

DEMO_TENANT_SLUG = "acme"

# actor, action, resource, status, risk, details, bundle_type, allowed, sensitivity, destination, blocked_hop, minutes_ago
DEMO_RAG_SCENARIOS = [
    (
        "compliance@acme.com",
        "RAG Ingest",
        "pinecone/ingest",
        "allowed",
        "low",
        "blocked_hop=none; hops=2; product FAQ indexed after governance checks",
        "conditional_rag",
        True,
        None,
        "pinecone",
        None,
        35,
    ),
    (
        "security@acme.com",
        "RAG Ingest",
        "pinecone/ingest",
        "blocked",
        "critical",
        "blocked_hop=document_to_embedding; hops=1; RESTRICTED_PII blocked before embedding",
        "conditional_rag",
        False,
        "RESTRICTED_PII",
        "pinecone",
        "document_to_embedding",
        28,
    ),
    (
        "auditor@acme.com",
        "RAG Ingest",
        "vector_store/ingest",
        "blocked",
        "critical",
        "blocked_hop=document_to_embedding; hops=1; RESTRICTED_PHI cannot reach vector store",
        "conditional_rag",
        False,
        "RESTRICTED_PHI",
        "vector_store",
        "document_to_embedding",
        22,
    ),
    (
        "developer@acme.com",
        "RAG Evaluate",
        "vector_store/upsert",
        "allowed",
        "low",
        "movement=document→vector_store; sensitivity=none; dry-run passed for investor summary",
        "data_movement",
        True,
        None,
        "vector_store",
        None,
        18,
    ),
    (
        "security@acme.com",
        "RAG Upsert",
        "pinecone/upsert",
        "blocked",
        "critical",
        "sensitivity=RESTRICTED_PCI; PCI card pattern blocked from Pinecone upsert",
        "data_movement",
        False,
        "RESTRICTED_PCI",
        "pinecone",
        None,
        12,
    ),
    (
        "admin@acme.com",
        "RAG Upsert",
        "pinecone/upsert",
        "allowed",
        "low",
        "sensitivity=none; public help-center article upserted (demo mock index)",
        "data_movement",
        True,
        None,
        "pinecone",
        None,
        6,
    ),
]


def _classification(sensitivity: str | None) -> dict:
    if sensitivity == "RESTRICTED_PII":
        return {
            "entities": ["SSN"],
            "sensitivity_labels": ["RESTRICTED_PII"],
            "highest_sensitivity": "RESTRICTED_PII",
            "match_count": 1,
            "region": "US",
        }
    if sensitivity == "RESTRICTED_PHI":
        return {
            "entities": ["PHI"],
            "sensitivity_labels": ["RESTRICTED_PHI"],
            "highest_sensitivity": "RESTRICTED_PHI",
            "match_count": 1,
            "region": "US",
        }
    if sensitivity == "RESTRICTED_PCI":
        return {
            "entities": ["PCI Card"],
            "sensitivity_labels": ["RESTRICTED_PCI"],
            "highest_sensitivity": "RESTRICTED_PCI",
            "match_count": 1,
            "region": "US",
        }
    return {
        "entities": [],
        "sensitivity_labels": [],
        "highest_sensitivity": None,
        "match_count": 0,
        "region": "US",
    }


def _control_mappings(sensitivity: str | None) -> list[str]:
    mapping = {
        "RESTRICTED_PII": ["ISO 27001 A.8.11", "ISO 27701 7.4.7", "HIPAA §164.514"],
        "RESTRICTED_PHI": ["HIPAA §164.502", "ISO 27701 7.4.7"],
        "RESTRICTED_PCI": ["PCI DSS 3.4", "ISO 27001 A.8.11"],
    }
    return mapping.get(sensitivity or "", [])


def _build_bundle_payload(
    *,
    bundle_id: uuid.UUID,
    actor: str,
    tenant_id: uuid.UUID,
    audit_event_id: uuid.UUID,
    bundle_type: str,
    allowed: bool,
    sensitivity: str | None,
    destination: str,
    blocked_hop: str | None,
    generated_at: datetime,
) -> dict:
    classification = _classification(sensitivity)
    if bundle_type == "conditional_rag":
        hops = [
            {
                "hop": "document_to_embedding",
                "from": "document",
                "to": "embedding",
                "operation": "embed",
                "allowed": blocked_hop != "document_to_embedding",
                "blocked_locally": blocked_hop == "document_to_embedding",
            },
        ]
        if blocked_hop != "document_to_embedding":
            hops.append(
                {
                    "hop": "embedding_to_vector_store",
                    "from": "embedding",
                    "to": destination,
                    "operation": "upsert",
                    "allowed": allowed,
                    "blocked_locally": False,
                }
            )
        return {
            "id": str(bundle_id),
            "generated_at": generated_at.isoformat(),
            "tenant_id": str(tenant_id),
            "actor": actor,
            "audit_event_id": str(audit_event_id),
            "bundle_type": "conditional_rag",
            "classification": classification,
            "pipeline": {
                "allowed": allowed,
                "blocked_hop": blocked_hop,
                "destination": destination,
                "vector_id": str(bundle_id) if allowed else None,
                "hops": hops,
            },
            "embedding": {
                "model": "text-embedding-3-small-mock",
                "source": "mock",
                "dimensions": 1536,
            }
            if allowed
            else None,
            "upsert": {
                "upserted": allowed,
                "vector_id": str(bundle_id),
                "count": 1 if allowed else 0,
                "mock": True,
                "error": None if allowed else "Blocked by data-movement policy",
            }
            if bundle_type == "conditional_rag" and (allowed or blocked_hop == "embedding_to_vector_store")
            else None,
            "control_mappings": _control_mappings(sensitivity),
        }

    return {
        "id": str(bundle_id),
        "generated_at": generated_at.isoformat(),
        "tenant_id": str(tenant_id),
        "actor": actor,
        "audit_event_id": str(audit_event_id),
        "bundle_type": "data_movement",
        "classification": classification,
        "movement": {"from": "document", "to": destination, "operation": "upsert"},
        "policy": {
            "engine": "opa",
            "allowed": allowed,
            "blocked_locally": bool(sensitivity),
            "skipped": False,
            "available": True,
            "violations": []
            if allowed
            else [
                {
                    "rule": "ABAC Data Movement Restriction",
                    "message": f"Sensitivity label {sensitivity} cannot be sent to {destination} (upsert)",
                    "severity": "critical",
                }
            ],
        },
        "control_mappings": _control_mappings(sensitivity),
    }


async def _ensure_demo_pinecone_settings(session, tenant_id: uuid.UUID) -> None:
    result = await session.execute(select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id))
    row = result.scalar_one_or_none()
    if row is None:
        row = TenantIntegration(tenant_id=tenant_id)
        session.add(row)
        await session.flush()
    if not row.pinecone_host:
        row.pinecone_enabled = True
        row.pinecone_host = "https://demo-index.svc.us-east-1.pinecone.io"
        row.pinecone_namespace = "acme-governed-rag"
        row.pinecone_dimension = 1536


async def seed_genai_dlp_for_tenant(session, tenant_id: uuid.UUID) -> bool:
    existing = await session.execute(
        select(GenaiEvidenceBundle.id).where(GenaiEvidenceBundle.tenant_id == tenant_id).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        return False

    await _ensure_demo_pinecone_settings(session, tenant_id)
    now = datetime.now(UTC)

    for scenario in DEMO_RAG_SCENARIOS:
        (
            actor,
            action,
            resource,
            status,
            risk,
            details,
            bundle_type,
            allowed,
            sensitivity,
            destination,
            blocked_hop,
            minutes_ago,
        ) = scenario
        timestamp = now - timedelta(minutes=minutes_ago)
        audit_id = uuid.uuid4()
        bundle_id = uuid.uuid4()
        usage_metadata = {
            "module": "rag_gateway",
            "classifications": _classification(sensitivity)["entities"],
            "sensitivity_labels": _classification(sensitivity)["sensitivity_labels"],
            "movement": {"to": destination, "operation": action.split()[-1].lower()},
            "evidence_bundle_id": str(bundle_id),
        }
        if blocked_hop:
            usage_metadata["blocked_hop"] = blocked_hop

        session.add(
            AuditLog(
                id=audit_id,
                tenant_id=tenant_id,
                timestamp=timestamp,
                actor=actor,
                action=action,
                resource=resource,
                status=status,
                risk=risk,
                details=details,
                usage_metadata=usage_metadata,
                source="internal",
            )
        )
        payload = _build_bundle_payload(
            bundle_id=bundle_id,
            actor=actor,
            tenant_id=tenant_id,
            audit_event_id=audit_id,
            bundle_type=bundle_type,
            allowed=allowed,
            sensitivity=sensitivity,
            destination=destination,
            blocked_hop=blocked_hop,
            generated_at=timestamp,
        )
        session.add(
            GenaiEvidenceBundle(
                id=bundle_id,
                tenant_id=tenant_id,
                actor=actor,
                payload=payload,
                created_at=timestamp,
            )
        )
    return True


async def reseed_genai_dlp_for_tenant(tenant_id: uuid.UUID) -> bool:
    async with async_session_factory() as session:
        await session.execute(delete(GenaiEvidenceBundle).where(GenaiEvidenceBundle.tenant_id == tenant_id))
        await session.execute(
            delete(AuditLog).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.action.in_(("RAG Evaluate", "RAG Upsert", "RAG Ingest")),
            )
        )
        inserted = await seed_genai_dlp_for_tenant(session, tenant_id)
        if inserted:
            await session.commit()
        return inserted


async def seed_genai_dlp_demo_events(*, force_tenant_id: uuid.UUID | None = None) -> int:
    """Seed demo RAG audit + evidence bundles. Returns number of tenants seeded."""
    if force_tenant_id is not None:
        return 1 if await reseed_genai_dlp_for_tenant(force_tenant_id) else 0

    async with async_session_factory() as session:
        tenant_result = await session.execute(select(Tenant))
        seeded = 0
        for tenant in tenant_result.scalars():
            if await seed_genai_dlp_for_tenant(session, tenant.id):
                seeded += 1
        if seeded:
            await session.commit()
        return seeded
