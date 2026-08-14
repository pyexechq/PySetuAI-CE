"""Time-bound break-glass exemptions for governed data movement."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import PolicyExemption
from app.services.dlp_classification import NEVER_EXEMPT_VECTOR_LABELS

DEFAULT_ALLOWED_DESTINATIONS = ["embedding", "llm"]
VECTOR_DESTINATIONS = {"pinecone", "vector_store", "embedding"}


@dataclass
class ExemptionContext:
    id: str
    reason: str
    ticket_ref: str | None
    allowed_destinations: list[str]
    expires_at: datetime


@dataclass
class ExemptionValidation:
    valid: bool
    context: ExemptionContext | None = None
    error: str | None = None


def exemption_blocks_local_override(
    sensitivity_labels: list[str],
    destination: str,
) -> bool:
    """Return True when break-glass cannot override the local guard."""
    if destination not in VECTOR_DESTINATIONS:
        return False
    if any(label in NEVER_EXEMPT_VECTOR_LABELS for label in sensitivity_labels):
        return True
    if "RESTRICTED_PII" in sensitivity_labels and destination in {"pinecone", "vector_store"}:
        return True
    return False


def exemption_allows_movement(
    context: ExemptionContext,
    *,
    destination: str,
    sensitivity_labels: list[str],
) -> ExemptionValidation:
    if destination not in context.allowed_destinations:
        return ExemptionValidation(
            valid=False,
            error=f"Exemption does not cover destination '{destination}'",
        )
    if exemption_blocks_local_override(sensitivity_labels, destination):
        return ExemptionValidation(
            valid=False,
            error="PHI/PCI cannot be exempted; restricted PII cannot be exempted to vector store upsert",
        )
    return ExemptionValidation(valid=True, context=context)


async def create_policy_exemption(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by: str,
    reason: str,
    ticket_ref: str | None = None,
    allowed_destinations: list[str] | None = None,
    duration_minutes: int = 60,
    max_uses: int | None = 1,
) -> PolicyExemption:
    destinations = allowed_destinations or list(DEFAULT_ALLOWED_DESTINATIONS)
    for dest in destinations:
        if dest in {"pinecone", "vector_store"}:
            raise ValueError("Break-glass exemptions cannot target vector store upsert destinations")

    row = PolicyExemption(
        tenant_id=tenant_id,
        created_by=created_by,
        reason=reason.strip(),
        ticket_ref=ticket_ref.strip() if ticket_ref else None,
        allowed_destinations=destinations,
        expires_at=datetime.now(UTC) + timedelta(minutes=max(5, min(duration_minutes, 24 * 60))),
        max_uses=max_uses,
    )
    db.add(row)
    await db.flush()
    return row


async def get_policy_exemption(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    exemption_id: str | uuid.UUID,
) -> PolicyExemption | None:
    try:
        lookup_id = exemption_id if isinstance(exemption_id, uuid.UUID) else uuid.UUID(str(exemption_id))
    except ValueError:
        return None
    result = await db.execute(
        select(PolicyExemption).where(
            PolicyExemption.id == lookup_id,
            PolicyExemption.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def validate_policy_exemption(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    exemption_id: str | None,
    destination: str,
    sensitivity_labels: list[str],
) -> ExemptionValidation:
    if not exemption_id:
        return ExemptionValidation(valid=False)

    row = await get_policy_exemption(db, tenant_id, exemption_id)
    if row is None:
        return ExemptionValidation(valid=False, error="Exemption not found")
    if row.revoked_at is not None:
        return ExemptionValidation(valid=False, error="Exemption has been revoked")
    now = datetime.now(UTC)
    if row.expires_at <= now:
        return ExemptionValidation(valid=False, error="Exemption has expired")
    if row.max_uses is not None and row.use_count >= row.max_uses:
        return ExemptionValidation(valid=False, error="Exemption use limit reached")

    context = ExemptionContext(
        id=str(row.id),
        reason=row.reason,
        ticket_ref=row.ticket_ref,
        allowed_destinations=list(row.allowed_destinations or []),
        expires_at=row.expires_at,
    )
    return exemption_allows_movement(context, destination=destination, sensitivity_labels=sensitivity_labels)


async def consume_policy_exemption(db: AsyncSession, row: PolicyExemption) -> None:
    row.use_count += 1
    await db.flush()


async def revoke_policy_exemption(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    exemption_id: str,
) -> PolicyExemption | None:
    row = await get_policy_exemption(db, tenant_id, exemption_id)
    if row is None:
        return None
    row.revoked_at = datetime.now(UTC)
    await db.flush()
    return row


async def list_active_policy_exemptions(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    limit: int = 50,
) -> list[PolicyExemption]:
    now = datetime.now(UTC)
    result = await db.execute(
        select(PolicyExemption)
        .where(
            PolicyExemption.tenant_id == tenant_id,
            PolicyExemption.revoked_at.is_(None),
            PolicyExemption.expires_at > now,
        )
        .order_by(PolicyExemption.expires_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


def exemption_to_opa_payload(context: ExemptionContext | None, *, valid: bool) -> dict:
    if not valid or context is None:
        return {"valid": False, "allowed_destinations": {}}
    return {
        "valid": True,
        "id": context.id,
        "reason": context.reason,
        "ticket_ref": context.ticket_ref or "",
        "expires_at": context.expires_at.isoformat(),
        "allowed_destinations": {dest: True for dest in context.allowed_destinations},
    }
