"""Map tenant policies to governance graph nodes."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import ClientApiKey, Policy, PolicyBundle

GRAPH_NODES: dict[str, dict[str, Any]] = {
    "gateway": {"label": "AI Gateway", "type": "gateway"},
    "router": {"label": "LLM Router", "type": "router"},
    "policy": {"label": "Policy Engine", "type": "policy"},
    "dlp": {"label": "DLP Scanner", "type": "dlp"},
    "mcp": {"label": "MCP Broker", "type": "mcp"},
    "audit": {"label": "Audit Log", "type": "audit"},
}


def resolve_policy_graph_node(policy_name: str) -> dict[str, Any]:
    name = policy_name.lower()
    if any(k in name for k in ("pii", "dlp", "redaction", "residency", "classification")):
        node_id = "dlp"
        edge_labels = ["scan"]
        description = "Data protection policies run at the DLP Scanner stage before downstream routing."
    elif any(k in name for k in ("mcp", "tool", "allowlist", "rate limit", "rate limiting")):
        node_id = "mcp"
        edge_labels = ["enforce"]
        description = "MCP governance policies enforce tool access at the MCP Broker."
    elif any(k in name for k in ("injection", "jailbreak", "exfil", "exfiltration", "toxic")):
        node_id = "policy"
        edge_labels = ["inspect", "enforce"]
        description = "Security policies evaluate content at the Policy Engine ingress checkpoint."
    else:
        node_id = "policy"
        edge_labels = ["inspect"]
        description = "Policy rules are enforced at the Policy Engine in the governance flow."

    node = GRAPH_NODES[node_id]
    return {
        "graph_node_id": node_id,
        "graph_node_label": node["label"],
        "graph_node_type": node["type"],
        "edge_labels": edge_labels,
        "description": description,
    }


async def _policies_for_bundle(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    bundle: PolicyBundle | None,
) -> list[Policy]:
    if bundle is None or bundle.status != "active":
        return []

    policy_ids = bundle.policy_ids if isinstance(bundle.policy_ids, list) else []
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
            Policy.id.in_(uuids),
            Policy.policy_type == "policy",
        )
    )
    policies_by_id = {str(p.id): p for p in result.scalars().all()}
    ordered: list[Policy] = []
    for raw in policy_ids:
        policy = policies_by_id.get(str(raw))
        if policy is not None:
            ordered.append(policy)
    return ordered


def _binding_from_policies(
    *,
    binding_id: str,
    name: str,
    bundle_id: str | None,
    bundle_name: str | None,
    is_default: bool,
    policies: list[Policy],
) -> dict[str, Any]:
    graph_node_ids: set[str] = {"gateway"}
    policy_items: list[dict[str, Any]] = []

    for policy in policies:
        mapping = resolve_policy_graph_node(policy.name)
        graph_node_ids.add(mapping["graph_node_id"])
        policy_items.append(
            {
                "policy_id": str(policy.id),
                "policy_name": policy.name,
                "policy_status": policy.status,
                "graph_node_id": mapping["graph_node_id"],
                "graph_node_label": mapping["graph_node_label"],
            }
        )

    return {
        "id": binding_id,
        "name": name,
        "bundle_id": bundle_id,
        "bundle_name": bundle_name,
        "is_default": is_default,
        "graph_node_ids": sorted(graph_node_ids),
        "policies": policy_items,
    }


async def build_ingress_bindings(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
    from app.services.policy_bundle_service import get_tenant_default_bundle

    bindings: list[dict[str, Any]] = []

    default_bundle = await get_tenant_default_bundle(db, tenant_id)
    if default_bundle is not None:
        default_policies = await _policies_for_bundle(db, tenant_id, default_bundle)
        bindings.append(
            _binding_from_policies(
                binding_id="__jwt_default__",
                name="JWT session (tenant default)",
                bundle_id=str(default_bundle.id),
                bundle_name=default_bundle.name,
                is_default=True,
                policies=default_policies,
            )
        )

    keys_result = await db.execute(
        select(ClientApiKey).where(ClientApiKey.tenant_id == tenant_id).order_by(ClientApiKey.name.asc())
    )
    keys = list(keys_result.scalars().all())
    if not keys:
        return bindings

    bundle_ids = {k.bundle_id for k in keys if k.bundle_id}
    bundles_by_id: dict[uuid.UUID, PolicyBundle] = {}
    if bundle_ids:
        bundle_rows = await db.execute(
            select(PolicyBundle).where(PolicyBundle.tenant_id == tenant_id, PolicyBundle.id.in_(bundle_ids))
        )
        bundles_by_id = {b.id: b for b in bundle_rows.scalars().all()}

    for key in keys:
        bundle = bundles_by_id.get(key.bundle_id) if key.bundle_id else None
        policies = await _policies_for_bundle(db, tenant_id, bundle)
        bindings.append(
            _binding_from_policies(
                binding_id=str(key.id),
                name=key.name,
                bundle_id=str(bundle.id) if bundle else None,
                bundle_name=bundle.name if bundle else None,
                is_default=False,
                policies=policies,
            )
        )

    return bindings
