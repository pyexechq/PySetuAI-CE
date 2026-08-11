"""Backfill recent DLP/residency audit samples for the Data Protection dashboard."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.db import async_session_factory
from app.db.seed_governance import DLP_CLASSIFICATION_RULES
from app.models.governance import AuditLog, Policy
from app.models.tenant import Tenant

RESIDENCY_POLICY_NAMES = ("PII Redaction — EU", "PII Redaction — US", "DLP Classification")

# actor, action, resource, status, risk, details
RESIDENCY_AUDIT_SAMPLES = [
    ("hr-bot@v1", "DLP Scan", "PII Redaction — EU", "review", "medium", "EU national ID redacted — Frankfurt hub"),
    ("finance-bot@v1", "PII", "PII Redaction — EU", "allowed", "low", "EU payroll IBAN masked"),
    ("support-agent@v1", "DLP Scan", "PII Redaction — EU", "review", "medium", "Cross-border EU PII in chat payload"),
    ("hr-bot@v1", "PII", "PII Redaction — EU", "allowed", "low", "Dublin hub processed EU employee record"),
    ("finance-bot@v1", "DLP Scan", "PII Redaction — EU", "review", "high", "EU VAT ID pattern detected"),
    ("sales-agent@v3", "PII", "PII Redaction — EU", "allowed", "low", "EU customer email tokenized"),
    ("hr-bot@v1", "DLP Scan", "PII Redaction — EU", "review", "medium", "EU residency gate passed after redaction"),
    ("support-agent@v1", "PII", "PII Redaction — EU", "allowed", "low", "Frankfurt region tag applied"),
    ("finance-bot@v1", "DLP Scan", "PII Redaction — EU", "review", "medium", "EU passport number redacted"),
    ("code-copilot@v2", "PII", "PII Redaction — EU", "allowed", "low", "EU developer PII scrubbed from logs"),
    ("hr-bot@v1", "DLP Scan", "PII Redaction — EU", "review", "medium", "EU GDPR field classification"),
    ("support-agent@v1", "PII", "PII Redaction — EU", "allowed", "low", "EU support ticket PII masked"),
    ("finance-bot@v1", "DLP Scan", "PII Redaction — EU", "review", "medium", "EU bank routing metadata removed"),
    ("sales-agent@v3", "PII", "PII Redaction — EU", "allowed", "low", "EU lead record sanitized"),
    ("hr-bot@v1", "DLP Scan", "PII Redaction — EU", "review", "medium", "EU tax ID redaction applied"),
    ("support-agent@v1", "PII", "PII Redaction — EU", "allowed", "low", "EU chat transcript redacted"),
    ("finance-bot@v1", "DLP Scan", "PII Redaction — EU", "review", "medium", "EU invoice PII removed"),
    ("sales-agent@v3", "PII", "PII Redaction — EU", "allowed", "low", "EU CRM export scrubbed"),
    ("finance-bot@v1", "DLP Scan", "PII Redaction — US", "review", "medium", "US SSN pattern redacted — Virginia hub"),
    ("sales-agent@v3", "PII", "PII Redaction — US", "allowed", "low", "US phone number masked"),
    ("support-agent@v1", "DLP Scan", "PII Redaction — US", "review", "medium", "US customer account number tokenized"),
    ("code-copilot@v2", "PII", "PII Redaction — US", "allowed", "low", "Oregon hub processed US employee SSN"),
    ("finance-bot@v1", "DLP Scan", "PII Redaction — US", "review", "high", "US routing number detected"),
    ("sales-agent@v3", "PII", "PII Redaction — US", "allowed", "low", "US billing address field redacted"),
    ("support-agent@v1", "DLP Scan", "PII Redaction — US", "review", "medium", "US residency policy applied"),
    ("finance-bot@v1", "PII", "PII Redaction — US", "allowed", "low", "US ACH metadata scrubbed"),
    ("code-copilot@v2", "DLP Scan", "PII Redaction — US", "review", "medium", "US developer token redacted"),
    ("sales-agent@v3", "PII", "PII Redaction — US", "allowed", "low", "US lead phone masked"),
    ("support-agent@v1", "DLP Scan", "PII Redaction — US", "review", "medium", "US chat PII removed"),
    ("finance-bot@v1", "PII", "PII Redaction — US", "allowed", "low", "US payroll export sanitized"),
    ("support-agent@v1", "LLM Request", "GPT-4o /chat", "allowed", "low", "Customer query processed"),
    ("code-copilot@v2", "Policy Check", "Prompt Injection Guard", "blocked", "high", "Detected override attempt"),
    ("hr-bot@v1", "MCP Tool Call", "HR Database /query", "allowed", "low", "Employee lookup"),
    ("unknown-client", "Auth Attempt", "AI Gateway", "blocked", "high", "Invalid JWT token"),
    ("sales-agent@v3", "LLM Request", "Claude 3.5 /chat", "allowed", "low", "Proposal draft generated"),
]


async def _recent_pii_count(session, tenant_id: uuid.UUID) -> int:
    now = datetime.now(UTC)
    range_start = now - timedelta(days=30)
    result = await session.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.timestamp >= range_start,
            AuditLog.timestamp < now,
            AuditLog.action.in_(("DLP Scan", "PII")),
        )
    )
    return result.scalar() or 0


async def _ensure_residency_policies(session, tenant_id: uuid.UUID) -> None:
    result = await session.execute(
        select(Policy).where(
            Policy.tenant_id == tenant_id,
            Policy.name.in_(RESIDENCY_POLICY_NAMES),
        )
    )
    for policy in result.scalars():
        if policy.status != "active":
            policy.status = "active"
        if policy.name == "DLP Classification" and not policy.rules:
            policy.rules = DLP_CLASSIFICATION_RULES


async def seed_data_protection_residency_for_tenant(session, tenant_id: uuid.UUID) -> bool:
    """Insert recent residency/DLP audit samples when the rolling window is sparse."""
    if await _recent_pii_count(session, tenant_id) >= 10:
        return False

    await _ensure_residency_policies(session, tenant_id)

    now = datetime.now(UTC)
    for index, row in enumerate(RESIDENCY_AUDIT_SAMPLES):
        day_offset = index % 21
        hour_offset = index % 12
        session.add(
            AuditLog(
                tenant_id=tenant_id,
                timestamp=now - timedelta(days=day_offset, hours=hour_offset, minutes=index % 45),
                actor=row[0],
                action=row[1],
                resource=row[2],
                status=row[3],
                risk=row[4],
                details=row[5],
            )
        )
    return True


async def seed_data_protection_residency_samples() -> None:
    async with async_session_factory() as session:
        tenant_result = await session.execute(select(Tenant))
        inserted = False
        for tenant in tenant_result.scalars():
            if await seed_data_protection_residency_for_tenant(session, tenant.id):
                inserted = True
        if inserted:
            await session.commit()
            print("Data protection seed: residency audit samples added.")
