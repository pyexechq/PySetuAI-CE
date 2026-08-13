from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog
from app.schemas.claude_compliance import ClaudeComplianceRecord, ClaudeComplianceSyncResponse
from app.services.dlp_service import scan_content


CLAUDE_COMPLIANCE_SOURCE = "claude_compliance"


def classify_sync_records(records: list[ClaudeComplianceRecord]) -> dict[str, object]:
    classifications: Counter[str] = Counter()
    dlp_matches = 0
    for record in records:
        result = scan_content(record.content)
        dlp_matches += result.match_count
        classifications.update(result.classifications)
    return {"dlp_matches": dlp_matches, "classifications": dict(sorted(classifications.items()))}


async def sync_claude_records(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    actor_name: str,
    records: list[ClaudeComplianceRecord],
) -> ClaudeComplianceSyncResponse:
    summary = classify_sync_records(records)
    users = {record.user_id for record in records}
    chats = {record.chat_id for record in records}

    for record in records:
        result = scan_content(record.content)
        status = "blocked" if result.has_pii and record.status == "blocked" else record.status
        db.add(
            AuditLog(
                tenant_id=tenant_id,
                timestamp=record.timestamp or datetime.now(UTC),
                actor=record.user_id,
                action=record.action,
                resource=record.chat_id,
                status=status,
                risk="high" if result.has_pii else "low",
                details=f"Claude organization {record.organization_id}; synced by {actor_name}; classifications: {', '.join(result.classifications) or 'none'}",
                usage_metadata={
                    "source": CLAUDE_COMPLIANCE_SOURCE,
                    "organization_id": record.organization_id,
                    "user_id": record.user_id,
                    "chat_id": record.chat_id,
                    "classifications": result.classifications,
                    "dlp_match_count": result.match_count,
                },
                source=CLAUDE_COMPLIANCE_SOURCE,
                external_id=record.chat_id,
            )
        )

    return ClaudeComplianceSyncResponse(
        source=CLAUDE_COMPLIANCE_SOURCE,
        records_received=len(records),
        records_synced=len(records),
        users_synced=len(users),
        chats_synced=len(chats),
        dlp_matches=int(summary["dlp_matches"]),
        classifications=summary["classifications"],
    )