"""Guardian policy enforcement loop and automated remediation (Phase 5).

Evaluates open anomalies, prompt-injection findings, exfiltration events, and
high-risk chain events against a severity→action policy, then executes
remediation (block agent, revoke access, quarantine, alert).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agentic import (
    AgentAnomalyRecord,
    AgentInventory,
    ExfiltrationEvent,
    GuardianAction,
    PromptInjectionFinding,
)

# Severity → remediation action mapping.
SEVERITY_ACTION_MAP: dict[str, str] = {
    "critical": "block_agent",
    "high": "revoke_access",
    "medium": "quarantine",
    "low": "alert",
}

# Trigger types that map to a remediation action.
TRIGGER_TYPES = ("anomaly", "prompt_injection", "exfiltration", "chain_risk")


def action_for_severity(severity: str) -> str:
    return SEVERITY_ACTION_MAP.get(severity, "alert")


def guardian_action_to_dict(action: GuardianAction) -> dict[str, Any]:
    return {
        "id": str(action.id),
        "tenant_id": str(action.tenant_id),
        "agent_id": str(action.agent_id) if action.agent_id else None,
        "endpoint_id": str(action.endpoint_id) if action.endpoint_id else None,
        "trigger_type": action.trigger_type,
        "trigger_id": str(action.trigger_id) if action.trigger_id else None,
        "action_type": action.action_type,
        "action_status": action.action_status,
        "policy_id": action.policy_id,
        "policy_name": action.policy_name,
        "severity": action.severity,
        "details": action.details,
        "execution_result": action.execution_result,
        "created_at": action.created_at.isoformat() if action.created_at else None,
        "executed_at": action.executed_at.isoformat() if action.executed_at else None,
    }


async def _create_action(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    agent_id: uuid.UUID | None,
    endpoint_id: uuid.UUID | None,
    trigger_type: str,
    trigger_id: uuid.UUID | None,
    action_type: str,
    severity: str,
    details: str,
    policy_id: str | None = None,
    policy_name: str = "",
) -> GuardianAction:
    action = GuardianAction(
        tenant_id=tenant_id,
        agent_id=agent_id,
        endpoint_id=endpoint_id,
        trigger_type=trigger_type,
        trigger_id=trigger_id,
        action_type=action_type,
        action_status="pending",
        policy_id=policy_id,
        policy_name=policy_name,
        severity=severity,
        details=details,
    )
    db.add(action)
    await db.flush()
    return action


async def _has_pending_action(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    trigger_type: str,
    trigger_id: uuid.UUID,
) -> bool:
    result = await db.execute(
        select(GuardianAction.id).where(
            GuardianAction.tenant_id == tenant_id,
            GuardianAction.trigger_type == trigger_type,
            GuardianAction.trigger_id == trigger_id,
            GuardianAction.action_status == "pending",
        )
    )
    return result.scalar_one_or_none() is not None


async def evaluate_agent_behavior(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    agent_id: uuid.UUID | None = None,
) -> list[GuardianAction]:
    """Evaluate open findings and produce pending GuardianActions (deduped)."""
    created: list[GuardianAction] = []

    anomaly_stmt = select(AgentAnomalyRecord).where(
        AgentAnomalyRecord.tenant_id == tenant_id,
        AgentAnomalyRecord.status == "open",
    )
    if agent_id:
        anomaly_stmt = anomaly_stmt.where(AgentAnomalyRecord.agent_id == agent_id)
    anomalies = (await db.execute(anomaly_stmt)).scalars().all()
    for anomaly in anomalies:
        if await _has_pending_action(db, tenant_id, "anomaly", anomaly.id):
            continue
        action_type = action_for_severity(anomaly.severity)
        created.append(
            await _create_action(
                db,
                tenant_id,
                agent_id=anomaly.agent_id,
                endpoint_id=anomaly.endpoint_id,
                trigger_type="anomaly",
                trigger_id=anomaly.id,
                action_type=action_type,
                severity=anomaly.severity,
                details=anomaly.description,
                policy_name="guardian",
            )
        )

    finding_stmt = select(PromptInjectionFinding).where(
        PromptInjectionFinding.tenant_id == tenant_id,
        PromptInjectionFinding.status == "open",
    )
    if agent_id:
        finding_stmt = finding_stmt.where(PromptInjectionFinding.agent_id == agent_id)
    findings = (await db.execute(finding_stmt)).scalars().all()
    for finding in findings:
        if await _has_pending_action(db, tenant_id, "prompt_injection", finding.id):
            continue
        action_type = action_for_severity(finding.highest_severity)
        created.append(
            await _create_action(
                db,
                tenant_id,
                agent_id=finding.agent_id,
                endpoint_id=finding.endpoint_id,
                trigger_type="prompt_injection",
                trigger_id=finding.id,
                action_type=action_type,
                severity=finding.highest_severity,
                details=f"Prompt injection in {finding.scan_target}",
                policy_name="guardian",
            )
        )

    exfil_stmt = select(ExfiltrationEvent).where(
        ExfiltrationEvent.tenant_id == tenant_id,
        ExfiltrationEvent.status == "open",
    )
    if agent_id:
        exfil_stmt = exfil_stmt.where(ExfiltrationEvent.agent_id == agent_id)
    exfil_events = (await db.execute(exfil_stmt)).scalars().all()
    for event in exfil_events:
        if await _has_pending_action(db, tenant_id, "exfiltration", event.id):
            continue
        severity = "critical" if event.risk_score >= 80 else "high" if event.risk_score >= 60 else "medium"
        action_type = action_for_severity(severity)
        created.append(
            await _create_action(
                db,
                tenant_id,
                agent_id=event.agent_id,
                endpoint_id=event.endpoint_id,
                trigger_type="exfiltration",
                trigger_id=event.id,
                action_type=action_type,
                severity=severity,
                details=f"Exfiltration ({event.exfil_type}) on {event.resource} via {event.tool}",
                policy_name="guardian",
            )
        )

    await db.flush()
    return created


async def _set_agent_status(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    agent_id: uuid.UUID | None,
    status: str,
) -> bool:
    if agent_id is None:
        return False
    result = await db.execute(
        select(AgentInventory).where(
            AgentInventory.tenant_id == tenant_id,
            AgentInventory.id == agent_id,
        )
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        return False
    agent.status = status
    await db.flush()
    return True


async def execute_remediation(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    action: GuardianAction,
) -> dict[str, Any]:
    """Execute a pending remediation action and record the result."""
    result: dict[str, Any] = {"action": action.action_type, "ok": False}
    try:
        if action.action_type == "block_agent":
            ok = await _set_agent_status(db, tenant_id, action.agent_id, "blocked")
            result.update({"ok": ok, "detail": "agent blocked"})
        elif action.action_type == "revoke_access":
            ok = await _set_agent_status(db, tenant_id, action.agent_id, "restricted")
            result.update({"ok": ok, "detail": "agent access revoked"})
        elif action.action_type == "quarantine":
            ok = await _set_agent_status(db, tenant_id, action.agent_id, "quarantined")
            result.update({"ok": ok, "detail": "agent quarantined"})
        elif action.action_type in ("alert", "notify"):
            from app.services.alert_webhook_service import build_gateway_alert_event, dispatch_tenant_alerts

            event = build_gateway_alert_event(
                action="agentic.guardian.alert",
                actor=str(action.agent_id) if action.agent_id else "guardian",
                resource=action.details,
                status="alert",
                risk=action.severity,
                details=action.details,
            )
            await dispatch_tenant_alerts(db, tenant_id, event)
            result.update({"ok": True, "detail": "alert dispatched"})
        else:
            result.update({"ok": False, "detail": f"unknown action {action.action_type}"})
    except Exception as exc:  # noqa: BLE001
        result.update({"ok": False, "detail": str(exc)})

    action.action_status = "executed" if result["ok"] else "failed"
    action.execution_result = result
    action.executed_at = datetime.now(UTC)
    await db.flush()
    return result


async def run_guardian_loop(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    agent_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Orchestrate: evaluate behavior → execute pending remediations."""
    created = await evaluate_agent_behavior(db, tenant_id, agent_id)

    pending_stmt = select(GuardianAction).where(
        GuardianAction.tenant_id == tenant_id,
        GuardianAction.action_status == "pending",
    )
    if agent_id:
        pending_stmt = pending_stmt.where(GuardianAction.agent_id == agent_id)
    pending = (await db.execute(pending_stmt)).scalars().all()

    executed = 0
    failed = 0
    for action in pending:
        result = await execute_remediation(db, tenant_id, action)
        if result["ok"]:
            executed += 1
        else:
            failed += 1

    await db.flush()
    return {
        "evaluated": len(created),
        "executed": executed,
        "failed": failed,
    }


async def list_guardian_actions(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    status: str | None = None,
    action_type: str | None = None,
) -> list[GuardianAction]:
    stmt = select(GuardianAction).where(GuardianAction.tenant_id == tenant_id)
    if status and status != "all":
        stmt = stmt.where(GuardianAction.action_status == status)
    if action_type and action_type != "all":
        stmt = stmt.where(GuardianAction.action_type == action_type)
    stmt = stmt.order_by(GuardianAction.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def guardian_summary(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, Any]:
    actions = (
        await db.execute(
            select(GuardianAction).where(GuardianAction.tenant_id == tenant_id)
        )
    ).scalars().all()
    pending = [a for a in actions if a.action_status == "pending"]
    executed = [a for a in actions if a.action_status == "executed"]
    failed = [a for a in actions if a.action_status == "failed"]
    by_action_type: dict[str, int] = {}
    for action in actions:
        by_action_type[action.action_type] = by_action_type.get(action.action_type, 0) + 1
    return {
        "total": len(actions),
        "pending": len(pending),
        "executed": len(executed),
        "failed": len(failed),
        "by_action_type": by_action_type,
    }
