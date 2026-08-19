"""Governed data-movement evaluation: DLP classification + OPA policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.dlp_service import DlpScanResult, scan_content
from app.services.data_movement_policy_service import (
    DEFAULT_DATA_MOVEMENT_POLICY,
    exemption_blocks_override,
    get_tenant_data_movement_policy,
    policy_blocks_movement,
    policy_to_opa_payload,
)
from app.services.opa_service import OpaDecision, build_data_movement_opa_input, evaluate_gateway_opa
from app.services.policy_exemption_service import (
    ExemptionContext,
    consume_policy_exemption,
    exemption_to_opa_payload,
    get_policy_exemption,
    validate_policy_exemption,
)

MovementDestination = Literal["llm", "pinecone", "vector_store", "embedding"]
MovementOperation = Literal["completion", "upsert", "query", "embed"]


@dataclass
class DataMovementResult:
    allowed: bool
    dlp: DlpScanResult
    opa: OpaDecision
    movement: dict[str, str]
    blocked_locally: bool = False
    exemption_applied: bool = False
    exemption_id: str | None = None
    exemption_error: str | None = None


def _local_vector_block(
    dlp: DlpScanResult,
    destination: str,
    *,
    exemption_valid: bool,
    policy: dict[str, list[str]] | None = None,
) -> bool:
    active_policy = policy or DEFAULT_DATA_MOVEMENT_POLICY
    if destination not in set(active_policy["vector_destinations"]):
        return False
    if exemption_valid and not exemption_blocks_override(
        active_policy,
        sensitivity_labels=dlp.sensitivity_labels,
        destination=destination,
    ):
        return False
    return policy_blocks_movement(
        active_policy,
        sensitivity_labels=dlp.sensitivity_labels,
        destination=destination,
    )


async def evaluate_content_movement(
    content: str,
    *,
    db: AsyncSession | None = None,
    tenant_uuid: UUID | None = None,
    destination: MovementDestination = "vector_store",
    operation: MovementOperation = "upsert",
    movement_from: str = "document",
    region: str = "US",
    tenant_id: str = "",
    bundle_name: str | None = None,
    role: str = "client_key",
    auth_type: str = "jwt",
    risk: str = "low",
    exemption_id: str | None = None,
    consume_exemption: bool = False,
) -> DataMovementResult:
    dlp = scan_content(content, region=region)
    movement = {"from": movement_from, "to": destination, "operation": operation}

    movement_policy = DEFAULT_DATA_MOVEMENT_POLICY
    movement_policy_customized = False
    if db and tenant_uuid:
        tenant_policy = await get_tenant_data_movement_policy(db, tenant_uuid)
        movement_policy = tenant_policy["policy"]
        movement_policy_customized = tenant_policy["is_customized"]

    exemption_valid = False
    exemption_context: ExemptionContext | None = None
    exemption_error: str | None = None
    if db and tenant_uuid and exemption_id:
        exemption_validation = await validate_policy_exemption(
            db,
            tenant_id=tenant_uuid,
            exemption_id=exemption_id,
            destination=destination,
            sensitivity_labels=dlp.sensitivity_labels,
            movement_policy=movement_policy,
        )
        exemption_valid = exemption_validation.valid
        exemption_context = exemption_validation.context
        if not exemption_valid:
            exemption_error = exemption_validation.error

    if _local_vector_block(dlp, destination, exemption_valid=exemption_valid, policy=movement_policy):
        return DataMovementResult(
            allowed=False,
            dlp=dlp,
            opa=OpaDecision(
                allow=False,
                violations=[],
                skipped=True,
                available=False,
            ),
            movement=movement,
            blocked_locally=True,
            exemption_applied=False,
            exemption_id=exemption_id,
            exemption_error=exemption_error or "Local data-movement guard blocked request",
        )

    payload = build_data_movement_opa_input(
        tenant_id=tenant_id,
        bundle_name=bundle_name,
        region=region,
        risk=risk if dlp.has_pii else "low",
        entity_classifications=dlp.classifications,
        sensitivity_labels=dlp.sensitivity_labels,
        highest_sensitivity_label=dlp.highest_sensitivity,
        movement_from=movement_from,
        movement_to=destination,
        movement_operation=operation,
        role=role,
        auth_type=auth_type,
        exemption=exemption_to_opa_payload(exemption_context, valid=exemption_valid),
        tenant_policy=policy_to_opa_payload(movement_policy, customized=movement_policy_customized),
    )
    opa = await evaluate_gateway_opa(payload)
    allowed = opa.allow

    if allowed and exemption_valid and consume_exemption and db and tenant_uuid and exemption_id:
        row = await get_policy_exemption(db, tenant_uuid, exemption_id)
        if row is not None:
            await consume_policy_exemption(db, row)

    return DataMovementResult(
        allowed=allowed,
        dlp=dlp,
        opa=opa,
        movement=movement,
        exemption_applied=exemption_valid and allowed,
        exemption_id=exemption_context.id if exemption_context and exemption_valid else None,
        exemption_error=exemption_error,
    )
