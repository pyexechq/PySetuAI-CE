from typing import Annotated
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.core.rbac import MANAGE_LLM_PROVIDERS, MANAGE_POLICIES, VIEW_AUDIT_LOGS, VIEW_COMPLIANCE, require_any_permission, require_permission
from app.db.session import get_db
from app.models.tenant import User
from app.schemas.rag_gateway import (
    GenaiEvidenceSummary,
    PolicyExemptionCreateRequest,
    PolicyExemptionResponse,
    RagIngestRequest,
    RagIngestResponse,
    RagMovementRequest,
    RagMovementResponse,
    RagMovementViolation,
    RagPipelineHopResponse,
    RagUpsertRequest,
    RagUpsertResponse,
)
from app.schemas.settings import RagGatewaySettingsResponse, RagGatewaySettingsUpdate
from app.services.conditional_rag_service import run_conditional_rag_pipeline
from app.services.data_movement_service import evaluate_content_movement
from app.services.embedding_service import embed_text
from app.services.evidence_bundle_service import (
    build_evidence_bundle,
    build_rag_pipeline_evidence_bundle,
    get_evidence_bundle,
    list_evidence_bundles,
    save_evidence_bundle,
)
from app.services.integration_service import get_or_create_integration, mask_secret, resolve_gateway_config
from app.services.pinecone_adapter import resolve_vector_store_config, upsert_vector
from app.services.policy_exemption_service import (
    create_policy_exemption,
    list_active_policy_exemptions,
    revoke_policy_exemption,
)
from app.services.rag_audit_service import write_rag_audit

router = APIRouter()

_require_rag_gateway = require_any_permission(VIEW_COMPLIANCE, VIEW_AUDIT_LOGS, MANAGE_POLICIES)
_require_rag_admin = require_permission(MANAGE_LLM_PROVIDERS)


def _movement_response(
    result,
    evidence_id: str | None,
    *,
    stub_note: str | None = None,
) -> RagMovementResponse:
    violations = [
        RagMovementViolation(rule=v.rule, message=v.message, severity=v.severity)
        for v in result.opa.violations
    ]
    if result.blocked_locally and not violations:
        violations.append(
            RagMovementViolation(
                rule="Local Data Movement Guard",
                message=(
                    f"Restricted sensitivity {result.dlp.highest_sensitivity} "
                    f"cannot be sent to {result.movement['to']}"
                ),
                severity="critical",
            )
        )
    return RagMovementResponse(
        allowed=result.allowed,
        classifications=result.dlp.classifications,
        sensitivity_labels=result.dlp.sensitivity_labels,
        highest_sensitivity=result.dlp.highest_sensitivity,
        movement=result.movement,
        violations=violations,
        evidence_bundle_id=evidence_id,
        stub_note=stub_note,
        exemption_applied=result.exemption_applied,
        exemption_error=result.exemption_error,
    )


def _risk_for_result(result) -> str:
    if result.dlp.highest_sensitivity in {"RESTRICTED_PII", "RESTRICTED_PHI", "RESTRICTED_PCI"}:
        return "critical"
    if result.dlp.has_pii:
        return "high"
    return "low"


async def _rag_settings_response(db: AsyncSession, tenant_id) -> RagGatewaySettingsResponse:
    config = await resolve_vector_store_config(db, tenant_id)
    return RagGatewaySettingsResponse(
        pinecone_enabled=config.enabled,
        pinecone_api_key_set=bool(config.api_key),
        pinecone_api_key_masked=config.api_key_masked,
        pinecone_host=config.host or "",
        pinecone_namespace=config.namespace,
        pinecone_dimension=config.dimension,
        embedding_model=settings.embedding_model,
        configured=bool(config.enabled and config.api_key and config.host),
        config_source=config.source,
    )


async def _persist_movement_evidence(
    db: AsyncSession,
    *,
    tenant_id,
    actor: str,
    result,
    audit_event_id: str,
) -> str:
    bundle = build_evidence_bundle(
        movement_result=result,
        tenant_id=str(tenant_id),
        actor=actor,
        audit_event_id=audit_event_id,
    )
    await save_evidence_bundle(db, tenant_id=tenant_id, actor=actor, payload=bundle)
    return bundle["id"]


def _exemption_response(row) -> PolicyExemptionResponse:
    status = "revoked" if row.revoked_at else ("expired" if row.expires_at <= datetime.now(UTC) else "active")
    return PolicyExemptionResponse(
        id=str(row.id),
        created_by=row.created_by,
        reason=row.reason,
        ticket_ref=row.ticket_ref,
        allowed_destinations=list(row.allowed_destinations or []),
        expires_at=row.expires_at.isoformat(),
        revoked_at=row.revoked_at.isoformat() if row.revoked_at else None,
        use_count=row.use_count,
        max_uses=row.max_uses,
        created_at=row.created_at.isoformat(),
        status=status,
    )


@router.get("/rag-gateway/settings", response_model=RagGatewaySettingsResponse)
async def get_rag_gateway_settings(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RagGatewaySettingsResponse:
    return await _rag_settings_response(db, current_user.tenant_id)


@router.put("/rag-gateway/settings", response_model=RagGatewaySettingsResponse)
async def update_rag_gateway_settings(
    payload: RagGatewaySettingsUpdate,
    current_user: Annotated[User, Depends(_require_rag_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RagGatewaySettingsResponse:
    row = await get_or_create_integration(db, current_user.tenant_id)
    if payload.pinecone_enabled is not None:
        row.pinecone_enabled = payload.pinecone_enabled
    if payload.pinecone_api_key is not None:
        row.pinecone_api_key = payload.pinecone_api_key.strip() or None
    if payload.pinecone_host is not None:
        row.pinecone_host = payload.pinecone_host.strip()
    if payload.pinecone_namespace is not None:
        row.pinecone_namespace = payload.pinecone_namespace.strip()
    if payload.pinecone_dimension is not None:
        row.pinecone_dimension = payload.pinecone_dimension
    await db.commit()
    await db.refresh(row)
    return await _rag_settings_response(db, current_user.tenant_id)


@router.post("/rag-gateway/evaluate", response_model=RagMovementResponse)
async def evaluate_rag_movement(
    payload: RagMovementRequest,
    current_user: Annotated[User, Depends(_require_rag_gateway)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RagMovementResponse:
    result = await evaluate_content_movement(
        payload.content,
        db=db,
        tenant_uuid=current_user.tenant_id,
        destination=payload.destination,
        operation=payload.operation,
        region=payload.region,
        tenant_id=str(current_user.tenant_id),
        bundle_name=payload.policy_bundle,
        role=current_user.role,
        auth_type="jwt",
        exemption_id=payload.exemption_id,
        consume_exemption=bool(payload.exemption_id),
    )
    audit_id = await write_rag_audit(
        db,
        tenant_id=current_user.tenant_id,
        actor=current_user.email,
        action="RAG Evaluate" if not result.exemption_applied else "RAG Exemption Applied",
        resource=f"{payload.destination}/{payload.operation}",
        status="allowed" if result.allowed else "blocked",
        risk=_risk_for_result(result),
        details=(
            f"movement={result.movement['from']}→{result.movement['to']}; "
            f"sensitivity={result.dlp.highest_sensitivity or 'none'}"
        ),
        usage_metadata={
            "classifications": result.dlp.classifications,
            "sensitivity_labels": result.dlp.sensitivity_labels,
            "movement": result.movement,
            "exemption_id": result.exemption_id,
            "exemption_applied": result.exemption_applied,
        },
    )
    evidence_id = await _persist_movement_evidence(
        db,
        tenant_id=current_user.tenant_id,
        actor=current_user.email,
        result=result,
        audit_event_id=str(audit_id),
    )
    await db.commit()
    return _movement_response(result, evidence_id)


@router.post("/rag-gateway/upsert", response_model=RagUpsertResponse)
async def governed_rag_upsert(
    payload: RagUpsertRequest,
    current_user: Annotated[User, Depends(_require_rag_gateway)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RagUpsertResponse:
    result = await evaluate_content_movement(
        payload.content,
        db=db,
        tenant_uuid=current_user.tenant_id,
        destination=payload.destination,
        operation="upsert",
        region=payload.region,
        tenant_id=str(current_user.tenant_id),
        bundle_name=payload.policy_bundle,
        role=current_user.role,
        auth_type="jwt",
        exemption_id=payload.exemption_id,
        consume_exemption=bool(payload.exemption_id),
    )
    audit_id = await write_rag_audit(
        db,
        tenant_id=current_user.tenant_id,
        actor=current_user.email,
        action="RAG Upsert" if not result.exemption_applied else "RAG Exemption Applied",
        resource=f"{payload.destination}/upsert",
        status="allowed" if result.allowed else "blocked",
        risk=_risk_for_result(result),
        details=f"sensitivity={result.dlp.highest_sensitivity or 'none'}",
        usage_metadata={
            "classifications": result.dlp.classifications,
            "sensitivity_labels": result.dlp.sensitivity_labels,
            "movement": result.movement,
            "exemption_id": result.exemption_id,
            "exemption_applied": result.exemption_applied,
        },
    )
    evidence_id = await _persist_movement_evidence(
        db,
        tenant_id=current_user.tenant_id,
        actor=current_user.email,
        result=result,
        audit_event_id=str(audit_id),
    )
    base = _movement_response(
        result,
        evidence_id,
        stub_note="Upsert blocked by data-movement policy." if not result.allowed else None,
    )

    vector_id = payload.document_id
    upserted = False
    note = base.stub_note
    if result.allowed:
        gateway = await resolve_gateway_config(db, current_user.tenant_id)
        vector_config = await resolve_vector_store_config(db, current_user.tenant_id)
        embedding = await embed_text(
            payload.content,
            api_key=gateway.openai_api_key,
            dimensions=vector_config.dimension,
        )
        vector_id = payload.document_id or evidence_id
        upsert_result = await upsert_vector(
            vector_config,
            vector_id=vector_id,
            values=embedding.vector,
            metadata={
                "highest_sensitivity": result.dlp.highest_sensitivity or "PUBLIC",
                "sensitivity_labels": result.dlp.sensitivity_labels,
            },
            namespace=payload.namespace,
        )
        upserted = upsert_result.upserted
        note = upsert_result.error or (
            "Vector upserted to Pinecone."
            if upserted
            else "Governance passed but Pinecone is not configured."
        )

    await db.commit()
    return RagUpsertResponse(**base.model_dump(), upserted=upserted, vector_id=vector_id, stub_note=note)


@router.post("/rag-gateway/ingest", response_model=RagIngestResponse)
async def governed_rag_ingest(
    payload: RagIngestRequest,
    current_user: Annotated[User, Depends(_require_rag_gateway)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RagIngestResponse:
    pipeline = await run_conditional_rag_pipeline(
        payload.content,
        db=db,
        tenant_id=current_user.tenant_id,
        destination=payload.destination,
        region=payload.region,
        bundle_name=payload.policy_bundle,
        role=current_user.role,
        auth_type="jwt",
        document_id=payload.document_id,
        namespace=payload.namespace,
        exemption_id=payload.exemption_id,
    )
    dlp = pipeline.dlp
    audit_id = await write_rag_audit(
        db,
        tenant_id=current_user.tenant_id,
        actor=current_user.email,
        action="RAG Ingest",
        resource=f"{payload.destination}/ingest",
        status="allowed" if pipeline.allowed else "blocked",
        risk="critical" if dlp and dlp.highest_sensitivity in {"RESTRICTED_PII", "RESTRICTED_PHI", "RESTRICTED_PCI"} else "low",
        details=f"blocked_hop={pipeline.blocked_hop or 'none'}; hops={len(pipeline.hops)}",
        usage_metadata={
            "blocked_hop": pipeline.blocked_hop,
            "hops": [
                {
                    "hop": hop.hop,
                    "allowed": hop.allowed,
                    "to": hop.movement_to,
                }
                for hop in pipeline.hops
            ],
            "classifications": dlp.classifications if dlp else [],
            "sensitivity_labels": dlp.sensitivity_labels if dlp else [],
        },
    )
    bundle = build_rag_pipeline_evidence_bundle(
        pipeline=pipeline,
        tenant_id=str(current_user.tenant_id),
        actor=current_user.email,
    )
    bundle["audit_event_id"] = str(audit_id)
    await save_evidence_bundle(
        db,
        tenant_id=current_user.tenant_id,
        actor=current_user.email,
        payload=bundle,
    )
    await db.commit()

    note = None
    if not pipeline.allowed:
        note = f"Blocked at hop: {pipeline.blocked_hop}"
    elif pipeline.upsert and pipeline.upsert.mock:
        note = pipeline.upsert.error or "Governance passed; configure Pinecone to complete upsert."
    elif pipeline.upsert and pipeline.upsert.upserted:
        note = "Conditional RAG pipeline completed — vector upserted."

    return RagIngestResponse(
        allowed=pipeline.allowed,
        blocked_hop=pipeline.blocked_hop,
        hops=[
            RagPipelineHopResponse(
                hop=hop.hop,
                movement_from=hop.movement_from,
                movement_to=hop.movement_to,
                operation=hop.operation,
                allowed=hop.allowed,
                blocked_locally=hop.blocked_locally,
            )
            for hop in pipeline.hops
        ],
        classifications=dlp.classifications if dlp else [],
        sensitivity_labels=dlp.sensitivity_labels if dlp else [],
        highest_sensitivity=dlp.highest_sensitivity if dlp else None,
        vector_id=pipeline.vector_id,
        upserted=bool(pipeline.upsert and pipeline.upsert.upserted),
        embedding_source=pipeline.embedding.source if pipeline.embedding else None,
        evidence_bundle_id=bundle["id"],
        note=note,
        exemption_applied=bool(payload.exemption_id) and pipeline.allowed,
        exemption_error=None,
    )


@router.get("/rag-gateway/exemptions", response_model=list[PolicyExemptionResponse])
async def list_policy_exemptions(
    current_user: Annotated[User, Depends(_require_rag_gateway)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PolicyExemptionResponse]:
    rows = await list_active_policy_exemptions(db, current_user.tenant_id)
    return [_exemption_response(row) for row in rows]


@router.post("/rag-gateway/exemptions", response_model=PolicyExemptionResponse, status_code=status.HTTP_201_CREATED)
async def create_policy_exemption_route(
    payload: PolicyExemptionCreateRequest,
    current_user: Annotated[User, Depends(_require_rag_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyExemptionResponse:
    try:
        row = await create_policy_exemption(
            db,
            tenant_id=current_user.tenant_id,
            created_by=current_user.email,
            reason=payload.reason,
            ticket_ref=payload.ticket_ref,
            allowed_destinations=list(payload.allowed_destinations) if payload.allowed_destinations else None,
            duration_minutes=payload.duration_minutes,
            max_uses=payload.max_uses,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await write_rag_audit(
        db,
        tenant_id=current_user.tenant_id,
        actor=current_user.email,
        action="Policy Exemption Created",
        resource="rag-gateway/exemptions",
        status="allowed",
        risk="high",
        details=payload.reason[:500],
        usage_metadata={
            "exemption_id": str(row.id),
            "allowed_destinations": row.allowed_destinations,
            "expires_at": row.expires_at.isoformat(),
            "ticket_ref": row.ticket_ref,
        },
    )
    await db.commit()
    await db.refresh(row)
    return _exemption_response(row)


@router.delete("/rag-gateway/exemptions/{exemption_id}", response_model=PolicyExemptionResponse)
async def revoke_policy_exemption_route(
    exemption_id: str,
    current_user: Annotated[User, Depends(_require_rag_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PolicyExemptionResponse:
    row = await revoke_policy_exemption(db, current_user.tenant_id, exemption_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exemption not found")
    await write_rag_audit(
        db,
        tenant_id=current_user.tenant_id,
        actor=current_user.email,
        action="Policy Exemption Revoked",
        resource=f"rag-gateway/exemptions/{exemption_id}",
        status="allowed",
        risk="medium",
        details=f"Revoked exemption {exemption_id}",
    )
    await db.commit()
    await db.refresh(row)
    return _exemption_response(row)


@router.get("/rag-gateway/evidence", response_model=list[GenaiEvidenceSummary])
async def list_genai_evidence(
    current_user: Annotated[User, Depends(_require_rag_gateway)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
) -> list[GenaiEvidenceSummary]:
    rows = await list_evidence_bundles(db, current_user.tenant_id, limit=limit)
    summaries: list[GenaiEvidenceSummary] = []
    for row in rows:
        payload = row.payload or {}
        classification = payload.get("classification") or {}
        pipeline = payload.get("pipeline") or {}
        policy = payload.get("policy") or {}
        summaries.append(
            GenaiEvidenceSummary(
                id=str(row.id),
                created_at=row.created_at.isoformat(),
                actor=row.actor,
                bundle_type=str(payload.get("bundle_type", "data_movement")),
                allowed=bool(pipeline.get("allowed", policy.get("allowed", False))),
                highest_sensitivity=classification.get("highest_sensitivity"),
                destination=pipeline.get("destination") or (payload.get("movement") or {}).get("to"),
                blocked_hop=pipeline.get("blocked_hop"),
            )
        )
    return summaries


@router.get("/rag-gateway/evidence/{bundle_id}/export")
async def export_genai_evidence(
    bundle_id: str,
    current_user: Annotated[User, Depends(_require_rag_gateway)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    row = await get_evidence_bundle(db, current_user.tenant_id, bundle_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence bundle not found")
    stamp = row.created_at.strftime("%Y%m%d")
    return JSONResponse(
        content=row.payload,
        headers={"Content-Disposition": f'attachment; filename="genai-evidence-{stamp}-{bundle_id}.json"'},
    )


@router.get("/rag-gateway/iac-evidence")
async def scan_iac_evidence(
    current_user: Annotated[User, Depends(_require_rag_gateway)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.services.iac_evidence_config_service import run_tenant_iac_scan

    return await run_tenant_iac_scan(db, current_user.tenant_id)


@router.post("/rag-gateway/demo-events")
async def create_demo_rag_events(
    current_user: Annotated[User, Depends(_require_rag_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not settings.debug:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    from app.db.seed_genai_dlp import reseed_genai_dlp_for_tenant

    created = await reseed_genai_dlp_for_tenant(current_user.tenant_id)
    summaries = await list_evidence_bundles(db, current_user.tenant_id, limit=20)
    return {
        "seeded": created,
        "evidence_count": len(summaries),
        "message": "Demo RAG audit events and evidence bundles created.",
    }
