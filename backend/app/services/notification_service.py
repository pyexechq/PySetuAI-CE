from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog
from app.schemas.notifications import NotificationListResponse, NotificationResponse


def _should_notify(log: AuditLog) -> bool:
    """Only surface actionable security alerts — not routine audit/routing detail."""
    if log.status == "blocked":
        return True
    if log.risk in {"high", "critical"}:
        return True
    if log.status == "review" and log.risk in {"high", "critical"}:
        return True
    return False


def _category(log: AuditLog) -> str:
    if "LLM" in log.action or "Gateway" in log.action:
        return "gateway"
    if "MCP" in log.action:
        return "mcp"
    if "Policy" in log.action or "DLP" in log.action:
        return "policy"
    return "security"


def _title(log: AuditLog) -> tuple[str, str]:
    category = _category(log)

    if log.status == "blocked":
        if category == "gateway":
            return "critical", "Gateway request blocked"
        if category == "mcp":
            return "critical", "MCP tool call blocked"
        if category == "policy":
            return "critical", "Policy violation blocked"
        return "critical", "Request blocked"

    if log.risk == "critical":
        return "critical", "Critical security event"

    if log.status == "review":
        return "warning", "Review required"

    if log.risk == "high":
        return "warning", "High-risk activity detected"

    return "info", "Security alert"


def _summary_message(log: AuditLog) -> str:
    category = _category(log)

    if log.status == "blocked":
        if category == "gateway":
            return "A gateway request was blocked. Open Audit Explorer for full trace and policy details."
        if category == "mcp":
            return "An MCP tool call was blocked. Open Audit Explorer for full details."
        if category == "policy":
            return "A policy rule blocked this activity. Open Audit Explorer for full details."
        return "This activity was blocked by security policy. Open Audit Explorer for full details."

    if log.risk == "critical":
        return "Critical risk detected. Review in Audit Explorer."

    if log.status == "review":
        return "This event needs review. Open Audit Explorer for full details."

    if log.risk == "high":
        return "High-risk activity detected. Review in Audit Explorer."

    return "Open Audit Explorer for full details."


def _classify(log: AuditLog) -> NotificationResponse | None:
    if not _should_notify(log):
        return None

    severity, title = _title(log)

    return NotificationResponse(
        id=str(log.id),
        title=title,
        message=_summary_message(log),
        severity=severity,
        category=_category(log),
        timestamp=log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        action=log.action,
        resource=log.resource,
        status=log.status,
    )


async def list_notifications(
    db: AsyncSession,
    tenant_id: UUID,
    read_ids: set[str] | None = None,
    limit: int = 30,
) -> NotificationListResponse:
    since = datetime.now(UTC) - timedelta(days=7)
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.timestamp >= since,
            or_(
                AuditLog.status == "blocked",
                AuditLog.status == "review",
                AuditLog.risk.in_(["high", "critical"]),
            ),
        )
        .order_by(AuditLog.timestamp.desc())
        .limit(limit * 3)
    )

    read = read_ids or set()
    notifications: list[NotificationResponse] = []
    for log in result.scalars().all():
        item = _classify(log)
        if item is not None:
            notifications.append(item)
        if len(notifications) >= limit:
            break

    unread = sum(1 for n in notifications if n.id not in read)
    return NotificationListResponse(notifications=notifications, unread_count=unread)
