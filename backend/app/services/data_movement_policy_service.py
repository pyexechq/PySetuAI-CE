"""Tenant OPA data-movement policy configuration."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.integration_service import get_or_create_integration

SENSITIVITY_LABEL_OPTIONS: list[dict[str, str]] = [
    {"id": "PUBLIC", "label": "Public"},
    {"id": "INTERNAL", "label": "Internal"},
    {"id": "INTERNAL_PII", "label": "Internal PII"},
    {"id": "CONFIDENTIAL_FINANCIAL", "label": "Confidential financial"},
    {"id": "RESTRICTED_PII", "label": "Restricted PII"},
    {"id": "RESTRICTED_PHI", "label": "Restricted PHI"},
    {"id": "RESTRICTED_PCI", "label": "Restricted PCI"},
]

DESTINATION_OPTIONS: list[dict[str, str]] = [
    {"id": "llm", "label": "LLM completion"},
    {"id": "pinecone", "label": "Pinecone"},
    {"id": "vector_store", "label": "Vector store"},
    {"id": "embedding", "label": "Embedding pipeline"},
]

VECTOR_STORE_DESTINATIONS = frozenset({"pinecone", "vector_store"})

DEFAULT_DATA_MOVEMENT_POLICY: dict[str, list[str]] = {
    "restricted_labels": ["RESTRICTED_PII", "RESTRICTED_PHI", "RESTRICTED_PCI"],
    "vector_destinations": ["pinecone", "vector_store", "embedding"],
    "never_exempt_labels": ["RESTRICTED_PHI", "RESTRICTED_PCI"],
}


def _normalize_policy(raw: dict[str, Any]) -> dict[str, list[str]]:
    allowed_labels = {item["id"] for item in SENSITIVITY_LABEL_OPTIONS}
    allowed_destinations = {item["id"] for item in DESTINATION_OPTIONS}

    restricted_labels = [
        label
        for label in raw.get("restricted_labels", [])
        if isinstance(label, str) and label in allowed_labels
    ]
    vector_destinations = [
        dest
        for dest in raw.get("vector_destinations", [])
        if isinstance(dest, str) and dest in allowed_destinations
    ]
    never_exempt_labels = [
        label
        for label in raw.get("never_exempt_labels", [])
        if isinstance(label, str) and label in allowed_labels
    ]

    if not restricted_labels:
        raise ValueError("Select at least one restricted sensitivity label.")
    if not vector_destinations:
        raise ValueError("Select at least one vector destination to protect.")

    return {
        "restricted_labels": restricted_labels,
        "vector_destinations": vector_destinations,
        "never_exempt_labels": never_exempt_labels,
    }


def resolve_data_movement_policy(stored: dict[str, Any] | list | None) -> tuple[dict[str, list[str]], bool]:
    if isinstance(stored, dict) and stored:
        return _normalize_policy(stored), True
    return dict(DEFAULT_DATA_MOVEMENT_POLICY), False


def policy_blocks_movement(
    policy: dict[str, list[str]],
    *,
    sensitivity_labels: list[str],
    destination: str,
) -> bool:
    if destination not in set(policy["vector_destinations"]):
        return False
    restricted = set(policy["restricted_labels"])
    return any(label in restricted for label in sensitivity_labels)


def exemption_blocks_override(
    policy: dict[str, list[str]],
    *,
    sensitivity_labels: list[str],
    destination: str,
) -> bool:
    never_exempt = set(policy["never_exempt_labels"])
    if any(label in never_exempt for label in sensitivity_labels):
        return True
    if "RESTRICTED_PII" in sensitivity_labels and destination in VECTOR_STORE_DESTINATIONS:
        return True
    return False


def policy_to_opa_payload(policy: dict[str, list[str]], *, customized: bool) -> dict[str, Any]:
    return {
        "customized": customized,
        "restricted_labels": policy["restricted_labels"],
        "vector_destinations": policy["vector_destinations"],
        "never_exempt_labels": policy["never_exempt_labels"],
    }


async def get_tenant_data_movement_policy(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    row = await get_or_create_integration(db, tenant_id)
    policy, customized = resolve_data_movement_policy(row.data_movement_policy)
    return {
        "policy": policy,
        "is_customized": customized,
        "defaults": DEFAULT_DATA_MOVEMENT_POLICY,
        "label_options": SENSITIVITY_LABEL_OPTIONS,
        "destination_options": DESTINATION_OPTIONS,
        "opa_policy_path": "pysetu/gateway",
    }


async def save_tenant_data_movement_policy(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    policy: dict[str, Any],
) -> dict[str, Any]:
    row = await get_or_create_integration(db, tenant_id)
    row.data_movement_policy = _normalize_policy(policy)
    await db.commit()
    await db.refresh(row)
    return await get_tenant_data_movement_policy(db, tenant_id)


async def reset_tenant_data_movement_policy(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    row = await get_or_create_integration(db, tenant_id)
    row.data_movement_policy = None
    await db.commit()
    await db.refresh(row)
    return await get_tenant_data_movement_policy(db, tenant_id)
