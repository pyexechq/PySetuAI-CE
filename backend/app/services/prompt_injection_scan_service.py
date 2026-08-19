"""Prompt-injection scanning of files, repos, and MCP resources (Phase 5).

Wraps the existing pure ``injection_detection_service.scan_content`` and
persists findings. Only a truncated content preview is stored — never full raw
content.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agentic import PromptInjectionFinding
from app.services.injection_detection_service import scan_content

# Maximum characters of content preview stored on a finding.
CONTENT_PREVIEW_MAX = 500


def _truncate(content: str, limit: int = CONTENT_PREVIEW_MAX) -> str:
    if len(content) <= limit:
        return content
    return content[:limit] + "…"


def scan_text(
    content: str,
    *,
    target_type: str,
    target: str,
    agent_id: uuid.UUID | None = None,
    endpoint_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Scan content and return a finding-shaped dict (no DB)."""
    result = scan_content(content)
    return {
        "tenant_id": None,
        "agent_id": str(agent_id) if agent_id else None,
        "endpoint_id": str(endpoint_id) if endpoint_id else None,
        "scan_target_type": target_type,
        "scan_target": target,
        "content_preview": _truncate(content),
        "highest_severity": result.highest_severity,
        "detected": result.detected,
        "recommended_action": result.recommended_action,
        "matches": [
            {
                "rule_id": match.rule_id,
                "name": match.name,
                "category": match.category,
                "severity": match.severity,
                "detail": match.detail,
            }
            for match in result.matches
        ],
    }


async def persist_finding(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    finding: dict[str, Any],
) -> PromptInjectionFinding:
    record = PromptInjectionFinding(
        tenant_id=tenant_id,
        agent_id=uuid.UUID(finding["agent_id"]) if finding.get("agent_id") else None,
        endpoint_id=uuid.UUID(finding["endpoint_id"]) if finding.get("endpoint_id") else None,
        scan_target_type=finding["scan_target_type"],
        scan_target=finding["scan_target"],
        content_preview=finding["content_preview"],
        highest_severity=finding["highest_severity"],
        detected=finding["detected"],
        recommended_action=finding["recommended_action"],
        matches=finding["matches"],
        status="open",
    )
    db.add(record)
    await db.flush()
    return record


async def scan_mcp_resource(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    resource_uri: str,
    content: str,
    agent_id: uuid.UUID | None = None,
) -> PromptInjectionFinding | None:
    finding = scan_text(content, target_type="mcp_resource", target=resource_uri, agent_id=agent_id)
    if not finding["detected"]:
        return None
    return await persist_finding(db, tenant_id, finding)


async def scan_file(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    path: str,
    content: str,
    agent_id: uuid.UUID | None = None,
) -> PromptInjectionFinding | None:
    finding = scan_text(content, target_type="file", target=path, agent_id=agent_id)
    if not finding["detected"]:
        return None
    return await persist_finding(db, tenant_id, finding)


async def scan_repo(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    repo_url: str,
    files: list[tuple[str, str]],
    agent_id: uuid.UUID | None = None,
) -> list[PromptInjectionFinding]:
    created: list[PromptInjectionFinding] = []
    for path, content in files:
        finding = scan_text(content, target_type="repo", target=f"{repo_url}#{path}", agent_id=agent_id)
        if finding["detected"]:
            created.append(await persist_finding(db, tenant_id, finding))
    return created


def finding_to_dict(finding: PromptInjectionFinding) -> dict[str, Any]:
    return {
        "id": str(finding.id),
        "tenant_id": str(finding.tenant_id),
        "agent_id": str(finding.agent_id) if finding.agent_id else None,
        "endpoint_id": str(finding.endpoint_id) if finding.endpoint_id else None,
        "scan_target_type": finding.scan_target_type,
        "scan_target": finding.scan_target,
        "content_preview": finding.content_preview,
        "highest_severity": finding.highest_severity,
        "detected": finding.detected,
        "recommended_action": finding.recommended_action,
        "matches": finding.matches or [],
        "status": finding.status,
        "created_at": finding.created_at.isoformat() if finding.created_at else None,
    }


async def list_findings(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    status: str | None = None,
    severity: str | None = None,
    target_type: str | None = None,
) -> list[PromptInjectionFinding]:
    stmt = select(PromptInjectionFinding).where(PromptInjectionFinding.tenant_id == tenant_id)
    if status and status != "all":
        stmt = stmt.where(PromptInjectionFinding.status == status)
    if severity and severity != "all":
        stmt = stmt.where(PromptInjectionFinding.highest_severity == severity)
    if target_type and target_type != "all":
        stmt = stmt.where(PromptInjectionFinding.scan_target_type == target_type)
    stmt = stmt.order_by(PromptInjectionFinding.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def acknowledge_finding(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    finding_id: uuid.UUID,
) -> PromptInjectionFinding | None:
    result = await db.execute(
        select(PromptInjectionFinding).where(
            PromptInjectionFinding.tenant_id == tenant_id,
            PromptInjectionFinding.id == finding_id,
        )
    )
    finding = result.scalar_one_or_none()
    if finding is None:
        return None
    finding.status = "acknowledged"
    await db.flush()
    return finding


async def finding_summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    findings = (
        await db.execute(
            select(PromptInjectionFinding).where(PromptInjectionFinding.tenant_id == tenant_id)
        )
    ).scalars().all()
    open_findings = [f for f in findings if f.status == "open"]
    by_severity: dict[str, int] = {}
    by_target_type: dict[str, int] = {}
    for finding in open_findings:
        by_severity[finding.highest_severity] = by_severity.get(finding.highest_severity, 0) + 1
        by_target_type[finding.scan_target_type] = by_target_type.get(finding.scan_target_type, 0) + 1
    return {
        "total": len(findings),
        "open": len(open_findings),
        "by_severity": by_severity,
        "by_target_type": by_target_type,
    }
