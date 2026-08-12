"""Policy bundle loading and tenant defaults."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import Policy, PolicyBundle


async def get_policy_bundle(db: AsyncSession, tenant_id: uuid.UUID, bundle_id: str) -> PolicyBundle:
    from fastapi import HTTPException, status

    try:
        bundle_uuid = uuid.UUID(bundle_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bundle id") from exc

    result = await db.execute(
        select(PolicyBundle).where(PolicyBundle.id == bundle_uuid, PolicyBundle.tenant_id == tenant_id)
    )
    bundle = result.scalar_one_or_none()
    if bundle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy bundle not found")
    return bundle


async def get_tenant_default_bundle(db: AsyncSession, tenant_id: uuid.UUID) -> PolicyBundle | None:
    result = await db.execute(
        select(PolicyBundle).where(
            PolicyBundle.tenant_id == tenant_id,
            PolicyBundle.is_default.is_(True),
            PolicyBundle.status == "active",
        )
    )
    return result.scalar_one_or_none()


async def load_bundle_rules(db: AsyncSession, tenant_id: uuid.UUID, bundle: PolicyBundle | None) -> list[dict]:
    if bundle is None or bundle.status != "active":
        return []

    policy_ids = bundle.policy_ids if isinstance(bundle.policy_ids, list) else []
    if not policy_ids:
        return []

    uuids: list[uuid.UUID] = []
    for raw in policy_ids:
        try:
            uuids.append(uuid.UUID(str(raw)))
        except ValueError:
            continue
    if not uuids:
        return []

    result = await db.execute(
        select(Policy).where(
            Policy.tenant_id == tenant_id,
            Policy.status == "active",
        )
    )
    all_policies = result.scalars().all()
    
    policies_by_id = {str(p.id): p for p in all_policies}
    children_by_parent: dict[str, list[Policy]] = {}
    for p in all_policies:
        pid = str(p.parent_id) if p.parent_id else None
        if pid:
            children_by_parent.setdefault(pid, []).append(p)

    def _resolve_policies(node_id: str, visited: set) -> list[Policy]:
        if node_id in visited:
            return []
        visited.add(node_id)
        node = policies_by_id.get(node_id)
        if not node:
            return []
        
        resolved = []
        if node.policy_type == "policy":
            resolved.append(node)
        elif node.policy_type == "folder":
            for child in children_by_parent.get(node_id, []):
                resolved.extend(_resolve_policies(str(child.id), visited))
        return resolved

    resolved_policies: list[Policy] = []
    visited = set()
    for raw_id in policy_ids:
        resolved_policies.extend(_resolve_policies(str(raw_id), visited))

    merged: list[dict] = []
    for policy in resolved_policies:
        if not policy.rules:
            continue
        for rule in policy.rules:
            if isinstance(rule, dict) and rule.get("enabled", True):
                merged.append({**rule, "policy_name": policy.name})
    return merged


async def clear_other_defaults(db: AsyncSession, tenant_id: uuid.UUID, except_id: uuid.UUID | None = None) -> None:
    result = await db.execute(
        select(PolicyBundle).where(PolicyBundle.tenant_id == tenant_id, PolicyBundle.is_default.is_(True))
    )
    for bundle in result.scalars().all():
        if except_id is None or bundle.id != except_id:
            bundle.is_default = False
