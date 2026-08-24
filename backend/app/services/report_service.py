from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog, LLMProvider, MCPServer, ReportDefinition

FREQUENCY_LABELS = {
    "on_demand": "On demand",
    "daily": "Daily",
    "weekly": "Weekly",
    "monthly": "Monthly",
    "quarterly": "Quarterly",
}

BUILTIN_REPORTS: list[dict[str, Any]] = [
    {
        "slug": "monthly-governance",
        "name": "Monthly Governance Summary",
        "description": "Executive overview of policy enforcement, blocks, and compliance posture",
        "category": "Executive",
        "format": "PDF",
        "query": {"source": "audit_logs", "filters": {"days_back": 30}, "limit": 5000},
        "schedule_frequency": "monthly",
        "schedule_enabled": False,
        "schedule_time": "09:00",
        "schedule_day_of_month": 1,
    },
    {
        "slug": "audit-export",
        "name": "Audit Log Export",
        "description": "Full tenant audit trail for compliance review",
        "category": "Compliance",
        "format": "CSV",
        "query": {"source": "audit_logs", "filters": {"days_back": 90}, "limit": 10000},
        "schedule_frequency": "on_demand",
        "schedule_enabled": False,
    },
    {
        "slug": "policy-violations",
        "name": "Policy Violation Report",
        "description": "Breakdown of blocked requests by rule and severity",
        "category": "Security",
        "format": "PDF",
        "query": {
            "source": "audit_logs",
            "filters": {"days_back": 7, "status": ["blocked"], "risk": ["high", "medium"]},
            "limit": 2000,
        },
        "schedule_frequency": "weekly",
        "schedule_enabled": False,
        "schedule_time": "08:00",
        "schedule_day_of_week": 1,
    },
    {
        "slug": "mcp-usage",
        "name": "MCP Usage & Trust Report",
        "description": "Tool call volumes, success rates, and trust scores per server",
        "category": "Operations",
        "format": "CSV",
        "query": {"source": "mcp_servers", "filters": {}, "limit": 500},
        "schedule_frequency": "weekly",
        "schedule_enabled": False,
        "schedule_time": "07:00",
        "schedule_day_of_week": 1,
    },
    {
        "slug": "llm-cost",
        "name": "LLM Routing & Cost Analysis",
        "description": "Model distribution, latency, and estimated cost savings",
        "category": "Finance",
        "format": "PDF",
        "query": {"source": "llm_providers", "filters": {}, "limit": 100},
        "schedule_frequency": "monthly",
        "schedule_enabled": True,
        "schedule_time": "06:00",
        "schedule_day_of_month": 1,
        "schedule_recipients": ["admin@acme.com"],
    },
    {
        "slug": "compounding-cost",
        "name": "Compounding Cost Optimization",
        "description": "Stacked savings from routing, dynamic MCP tools, and JSON/markdown compression",
        "category": "Finance",
        "format": "PDF",
        "query": {"source": "cost_optimization", "filters": {"days_back": 30}, "limit": 20},
        "schedule_frequency": "monthly",
        "schedule_enabled": False,
        "schedule_time": "06:30",
        "schedule_day_of_month": 1,
    },
    {
        "slug": "data-residency",
        "name": "Data Residency Compliance",
        "description": "Regional data placement and cross-border transfer summary",
        "category": "Compliance",
        "format": "PDF",
        "query": {
            "source": "data_residency",
            "filters": {"days_back": 90},
            "limit": 100,
        },
        "schedule_frequency": "quarterly",
        "schedule_enabled": False,
        "schedule_time": "09:00",
        "schedule_day_of_month": 1,
    },
    {
        "slug": "agentic-security",
        "name": "Agentic Security Posture",
        "description": "Anomalies, exfiltration, prompt-injection findings, and guardian actions",
        "category": "Security",
        "format": "PDF",
        "query": {"source": "agentic_security", "filters": {"days_back": 30}, "limit": 2000},
        "schedule_frequency": "weekly",
        "schedule_enabled": False,
        "schedule_time": "08:00",
        "schedule_day_of_week": 1,
    },
    {
        "slug": "copilot-governance",
        "name": "Microsoft Copilot Governance",
        "description": "Copilot instances, connectors, and governance drift findings",
        "category": "Compliance",
        "format": "CSV",
        "query": {"source": "copilot_governance", "filters": {}, "limit": 1000},
        "schedule_frequency": "monthly",
        "schedule_enabled": False,
        "schedule_time": "07:00",
        "schedule_day_of_month": 1,
    },
    {
        "slug": "mcp-tool-chains",
        "name": "MCP Tool Chain & Attack Surface",
        "description": "Tool chain events, chain risk scores, and per-tool policy coverage",
        "category": "Security",
        "format": "CSV",
        "query": {"source": "mcp_tool_chains", "filters": {"days_back": 30}, "limit": 2000},
        "schedule_frequency": "weekly",
        "schedule_enabled": False,
        "schedule_time": "07:30",
        "schedule_day_of_week": 1,
    },
    {
        "slug": "framework-rule-packs",
        "name": "Framework Rule Pack Coverage",
        "description": "Enforced compliance rule packs and their rule counts",
        "category": "Compliance",
        "format": "PDF",
        "query": {"source": "framework_rule_packs", "filters": {}, "limit": 100},
        "schedule_frequency": "monthly",
        "schedule_enabled": False,
        "schedule_time": "06:00",
        "schedule_day_of_month": 1,
    },
]

QUERY_TEMPLATES = [
    {
        "source": "audit_logs",
        "label": "Audit Logs",
        "description": "Tenant audit trail with policy and gateway events",
        "filter_fields": [
            {"key": "days_back", "label": "Lookback (days)", "type": "number", "default": 30},
            {"key": "status", "label": "Status", "type": "multi_select", "options": ["allowed", "blocked", "review"]},
            {"key": "risk", "label": "Risk level", "type": "multi_select", "options": ["low", "medium", "high"]},
            {"key": "action_contains", "label": "Action contains", "type": "text"},
            {"key": "actor_contains", "label": "Actor contains", "type": "text"},
        ],
    },
    {
        "source": "llm_providers",
        "label": "LLM Providers",
        "description": "Model routing volume, latency, and success rates",
        "filter_fields": [
            {"key": "provider_type", "label": "Provider type", "type": "text"},
            {"key": "min_requests", "label": "Minimum requests", "type": "number", "default": 0},
        ],
    },
    {
        "source": "mcp_servers",
        "label": "MCP Servers",
        "description": "MCP server usage, trust scores, and health status",
        "filter_fields": [
            {
                "key": "status",
                "label": "Health status",
                "type": "multi_select",
                "options": ["healthy", "degraded", "offline"],
            },
            {"key": "category", "label": "Category", "type": "text"},
        ],
    },
    {
        "source": "cost_optimization",
        "label": "Cost Optimization",
        "description": "Compounding savings from routing, tool ranking, and token compression",
        "filter_fields": [
            {"key": "days_back", "label": "Lookback (days)", "type": "number", "default": 30},
        ],
    },
    {
        "source": "data_residency",
        "label": "Data Residency",
        "description": "Regional data placement computed from residency policies and audit logs",
        "filter_fields": [
            {"key": "days_back", "label": "Lookback (days)", "type": "number", "default": 90},
        ],
    },
    {
        "source": "agentic_security",
        "label": "Agentic Security",
        "description": "Anomalies, exfiltration, prompt-injection findings, and guardian actions",
        "filter_fields": [
            {"key": "days_back", "label": "Lookback (days)", "type": "number", "default": 30},
        ],
    },
    {
        "source": "copilot_governance",
        "label": "Microsoft Copilot Governance",
        "description": "Copilot instances, connectors, and governance drift findings",
        "filter_fields": [],
    },
    {
        "source": "mcp_tool_chains",
        "label": "MCP Tool Chains",
        "description": "Tool chain events and chain risk scores",
        "filter_fields": [
            {"key": "days_back", "label": "Lookback (days)", "type": "number", "default": 30},
        ],
    },
    {
        "source": "framework_rule_packs",
        "label": "Framework Rule Packs",
        "description": "Enforced compliance rule packs and their rule counts",
        "filter_fields": [],
    },
]


def report_public_id(report: ReportDefinition) -> str:
    return report.slug or str(report.id)


def compute_next_run(report: ReportDefinition, from_dt: datetime | None = None) -> datetime | None:
    if not report.schedule_enabled or report.schedule_frequency == "on_demand":
        return None

    now = from_dt or datetime.now(UTC)
    hour, minute = (int(report.schedule_time.split(":")[0]), int(report.schedule_time.split(":")[1]))

    if report.schedule_frequency == "daily":
        candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    if report.schedule_frequency == "weekly":
        dow = report.schedule_day_of_week if report.schedule_day_of_week is not None else 0
        days_ahead = (dow - now.weekday()) % 7
        candidate = (now + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate

    if report.schedule_frequency in {"monthly", "quarterly"}:
        dom = report.schedule_day_of_month if report.schedule_day_of_month is not None else 1
        month = now.month
        year = now.year
        try:
            candidate = now.replace(day=dom, hour=hour, minute=minute, second=0, microsecond=0)
        except ValueError:
            candidate = now.replace(day=28, hour=hour, minute=minute, second=0, microsecond=0)
        if candidate <= now:
            if report.schedule_frequency == "monthly":
                month += 1
                if month > 12:
                    month = 1
                    year += 1
            else:
                month += 3
                while month > 12:
                    month -= 12
                    year += 1
            try:
                candidate = candidate.replace(year=year, month=month, day=dom)
            except ValueError:
                candidate = candidate.replace(year=year, month=month, day=28)
        return candidate

    return None


def report_status(report: ReportDefinition) -> str:
    if report.generation_status == "generating":
        return "generating"
    if report.schedule_enabled and report.schedule_frequency != "on_demand":
        return "scheduled"
    return "ready"


def report_frequency_label(report: ReportDefinition) -> str:
    if report.schedule_enabled and report.schedule_frequency != "on_demand":
        return FREQUENCY_LABELS.get(report.schedule_frequency, report.schedule_frequency)
    return FREQUENCY_LABELS.get(report.schedule_frequency, "On demand")


def catalog_item_dict(report: ReportDefinition) -> dict[str, Any]:
    last = report.last_generated_at or (datetime.now(UTC) - timedelta(days=3))
    last_result = report.last_run_result or {}
    return {
        "id": report_public_id(report),
        "report_uuid": str(report.id),
        "name": report.name,
        "description": report.description,
        "category": report.category,
        "frequency": report_frequency_label(report),
        "format": report.format,
        "last_generated": last.strftime("%Y-%m-%d"),
        "status": report_status(report),
        "query": report.query,
        "schedule": {
            "enabled": report.schedule_enabled,
            "frequency": report.schedule_frequency,
            "time": report.schedule_time,
            "day_of_week": report.schedule_day_of_week,
            "day_of_month": report.schedule_day_of_month,
            "next_run_at": report.next_run_at.isoformat() if report.next_run_at else None,
            "recipients": report.schedule_recipients or [],
        },
        "is_builtin": report.is_builtin,
        "last_delivery": last_result.get("delivery"),
        "stats": {
            "row_count": int(last_result.get("row_count") or 0),
            "generated_at": last_result.get("generated_at") or (last.isoformat() if report.last_generated_at else None),
        },
    }


async def ensure_tenant_reports(db: AsyncSession, tenant_id: UUID) -> None:
    result = await db.execute(select(func.count(ReportDefinition.id)).where(ReportDefinition.tenant_id == tenant_id))
    existing_count = result.scalar() or 0
    if existing_count == 0:
        now = datetime.now(UTC)
        for spec in BUILTIN_REPORTS:
            report = ReportDefinition(
                tenant_id=tenant_id,
                slug=spec["slug"],
                name=spec["name"],
                description=spec["description"],
                category=spec["category"],
                format=spec["format"],
                query=spec["query"],
                schedule_frequency=spec.get("schedule_frequency", "on_demand"),
                schedule_enabled=spec.get("schedule_enabled", False),
                schedule_time=spec.get("schedule_time", "09:00"),
                schedule_day_of_week=spec.get("schedule_day_of_week"),
                schedule_day_of_month=spec.get("schedule_day_of_month"),
                schedule_recipients=spec.get("schedule_recipients", []),
                last_generated_at=now - timedelta(days=3),
                is_builtin=True,
            )
            report.next_run_at = compute_next_run(report)
            db.add(report)
        await db.commit()
        return

    existing = await db.execute(
        select(ReportDefinition.slug).where(ReportDefinition.tenant_id == tenant_id, ReportDefinition.is_builtin.is_(True))
    )
    slugs = {row[0] for row in existing.all() if row[0]}
    added = False
    now = datetime.now(UTC)
    for spec in BUILTIN_REPORTS:
        if spec["slug"] in slugs:
            continue
        report = ReportDefinition(
            tenant_id=tenant_id,
            slug=spec["slug"],
            name=spec["name"],
            description=spec["description"],
            category=spec["category"],
            format=spec["format"],
            query=spec["query"],
            schedule_frequency=spec.get("schedule_frequency", "on_demand"),
            schedule_enabled=spec.get("schedule_enabled", False),
            schedule_time=spec.get("schedule_time", "09:00"),
            schedule_day_of_week=spec.get("schedule_day_of_week"),
            schedule_day_of_month=spec.get("schedule_day_of_month"),
            schedule_recipients=spec.get("schedule_recipients", []),
            last_generated_at=now - timedelta(days=3),
            is_builtin=True,
        )
        report.next_run_at = compute_next_run(report)
        db.add(report)
        added = True
    if added:
        await db.commit()


async def get_report_by_id(db: AsyncSession, tenant_id: UUID, report_id: str) -> ReportDefinition | None:
    result = await db.execute(
        select(ReportDefinition).where(
            ReportDefinition.tenant_id == tenant_id,
            ReportDefinition.slug == report_id,
        )
    )
    report = result.scalar_one_or_none()
    if report is not None:
        return report

    try:
        uuid_id = UUID(report_id)
    except ValueError:
        return None
    result = await db.execute(
        select(ReportDefinition).where(ReportDefinition.tenant_id == tenant_id, ReportDefinition.id == uuid_id)
    )
    return result.scalar_one_or_none()


async def execute_report_query(
    db: AsyncSession,
    tenant_id: UUID,
    query: dict[str, Any],
) -> tuple[list[str], list[list[Any]]]:
    source = query.get("source", "audit_logs")
    filters = query.get("filters") or {}
    limit = int(query.get("limit") or 1000)

    if source == "audit_logs":
        stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
        days_back = filters.get("days_back")
        if days_back:
            cutoff = datetime.now(UTC) - timedelta(days=int(days_back))
            stmt = stmt.where(AuditLog.timestamp >= cutoff)
        statuses = filters.get("status")
        if statuses:
            stmt = stmt.where(AuditLog.status.in_(statuses if isinstance(statuses, list) else [statuses]))
        risks = filters.get("risk")
        if risks:
            stmt = stmt.where(AuditLog.risk.in_(risks if isinstance(risks, list) else [risks]))
        action_contains = filters.get("action_contains")
        if action_contains:
            stmt = stmt.where(AuditLog.action.ilike(f"%{action_contains}%"))
        actor_contains = filters.get("actor_contains")
        if actor_contains:
            stmt = stmt.where(AuditLog.actor.ilike(f"%{actor_contains}%"))
        stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        columns = ["timestamp", "actor", "action", "resource", "status", "risk", "details"]
        data = [
            [
                r.timestamp.isoformat(),
                r.actor,
                r.action,
                r.resource,
                r.status,
                r.risk,
                r.details,
            ]
            for r in rows
        ]
        return columns, data

    if source == "llm_providers":
        stmt = select(LLMProvider).where(LLMProvider.tenant_id == tenant_id)
        provider_type = filters.get("provider_type")
        if provider_type:
            stmt = stmt.where(LLMProvider.provider_type.ilike(f"%{provider_type}%"))
        min_requests = filters.get("min_requests")
        if min_requests is not None:
            stmt = stmt.where(LLMProvider.total_requests >= int(min_requests))
        stmt = stmt.order_by(LLMProvider.total_requests.desc()).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        columns = ["name", "provider_type", "total_requests", "percentage", "avg_latency_ms", "success_rate"]
        data = [
            [r.name, r.provider_type, r.total_requests, r.percentage, r.avg_latency_ms, r.success_rate] for r in rows
        ]
        return columns, data

    if source == "mcp_servers":
        stmt = select(MCPServer).where(MCPServer.tenant_id == tenant_id)
        statuses = filters.get("status")
        if statuses:
            stmt = stmt.where(MCPServer.status.in_(statuses if isinstance(statuses, list) else [statuses]))
        category = filters.get("category")
        if category:
            stmt = stmt.where(MCPServer.category.ilike(f"%{category}%"))
        stmt = stmt.order_by(MCPServer.total_calls.desc()).limit(limit)
        rows = (await db.execute(stmt)).scalars().all()
        columns = ["name", "category", "total_calls", "success_rate", "trust_score", "risk_score", "status"]
        data = [
            [r.name, r.category, r.total_calls, r.success_rate, r.trust_score, r.risk_score, r.status] for r in rows
        ]
        return columns, data

    if source == "cost_optimization":
        from app.services.compounding_cost_service import compounding_table, summarize_compounding_savings

        days_back = int(filters.get("days_back") or 30)
        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        usage_rows = await db.execute(
            select(AuditLog.usage_metadata).where(
                AuditLog.tenant_id == tenant_id,
                AuditLog.timestamp >= cutoff,
                AuditLog.usage_metadata.is_not(None),
            )
        )
        summary = summarize_compounding_savings([row[0] for row in usage_rows.all()])
        return compounding_table(summary)

    if source == "data_residency":
        from app.services.data_protection_service import build_data_protection_overview

        overview = await build_data_protection_overview(db, tenant_id)
        columns = ["region", "name", "records", "percentage", "status", "hubs", "policy"]
        data = [
            [
                r.id,
                r.name,
                r.records,
                r.percentage,
                r.status,
                " · ".join(r.hubs),
                r.policy,
            ]
            for r in overview.regions
        ]
        return columns, data

    if source == "agentic_security":
        from datetime import timedelta as _td
        from app.models.agentic import (
            AgentAnomalyRecord,
            ExfiltrationEvent,
            GuardianAction,
            PromptInjectionFinding,
        )

        days_back = int(filters.get("days_back") or 30)
        cutoff = datetime.now(UTC) - _td(days=days_back)
        base = (AuditLog.tenant_id == tenant_id, AuditLog.timestamp >= cutoff)
        anomaly_n = (
            await db.execute(
                select(func.count(AgentAnomalyRecord.id)).where(
                    AgentAnomalyRecord.tenant_id == tenant_id,
                    AgentAnomalyRecord.created_at >= cutoff,
                )
            )
        ).scalar() or 0
        exfil_n = (
            await db.execute(
                select(func.count(ExfiltrationEvent.id)).where(
                    ExfiltrationEvent.tenant_id == tenant_id,
                    ExfiltrationEvent.created_at >= cutoff,
                )
            )
        ).scalar() or 0
        injection_n = (
            await db.execute(
                select(func.count(PromptInjectionFinding.id)).where(
                    PromptInjectionFinding.tenant_id == tenant_id,
                    PromptInjectionFinding.created_at >= cutoff,
                )
            )
        ).scalar() or 0
        guardian_n = (
            await db.execute(
                select(func.count(GuardianAction.id)).where(
                    GuardianAction.tenant_id == tenant_id,
                    GuardianAction.created_at >= cutoff,
                )
            )
        ).scalar() or 0
        columns = ["metric", "count"]
        data = [
            ["Anomalies detected", anomaly_n],
            ["Exfiltration events", exfil_n],
            ["Prompt injection findings", injection_n],
            ["Guardian actions", guardian_n],
        ]
        return columns, data

    if source == "copilot_governance":
        from app.models.copilot import CopilotConnector, CopilotDriftRecord, CopilotInstance

        inst_rows = await db.execute(
            select(CopilotInstance).where(CopilotInstance.tenant_id == tenant_id).limit(limit)
        )
        conn_rows = await db.execute(
            select(CopilotConnector).where(CopilotConnector.tenant_id == tenant_id).limit(limit)
        )
        drift_rows = await db.execute(
            select(CopilotDriftRecord).where(CopilotDriftRecord.tenant_id == tenant_id).limit(limit)
        )
        columns = ["entity", "name", "status", "risk_score", "detail"]
        data = [
            ["instance", r.name, r.status, r.risk_score, r.instance_type]
            for r in inst_rows.scalars().all()
        ]
        data += [
            ["connector", r.name, r.status, r.risk_score, r.connector_type]
            for r in conn_rows.scalars().all()
        ]
        data += [
            ["drift", r.entity_name, r.status, 0, f"{r.drift_type}: {r.description[:120]}"]
            for r in drift_rows.scalars().all()
        ]
        return columns, data

    if source == "mcp_tool_chains":
        from app.models.agentic import MCPToolChainEvent

        days_back = int(filters.get("days_back") or 30)
        cutoff = datetime.now(UTC) - timedelta(days=days_back)
        rows = await db.execute(
            select(MCPToolChainEvent)
            .where(
                MCPToolChainEvent.tenant_id == tenant_id,
                MCPToolChainEvent.created_at >= cutoff,
            )
            .order_by(MCPToolChainEvent.created_at.desc())
            .limit(limit)
        )
        columns = ["timestamp", "server", "tool", "decision", "chain_risk", "policy"]
        data = [
            [
                r.created_at.isoformat(),
                r.mcp_server_name,
                r.tool_name,
                r.decision,
                r.chain_risk_score,
                r.policy_name,
            ]
            for r in rows.scalars().all()
        ]
        return columns, data

    if source == "framework_rule_packs":
        from app.services.framework_rule_packs import list_framework_rule_packs

        packs = list_framework_rule_packs()
        columns = ["pack_id", "name", "version", "rule_count", "description"]
        data = [
            [p["id"], p["name"], p["version"], p["rule_count"], p["description"]]
            for p in packs
        ]
        return columns, data

    return [], []


async def run_report(
    db: AsyncSession,
    report: ReportDefinition,
) -> dict[str, Any]:
    columns, rows = await execute_report_query(db, report.tenant_id, report.query)
    generated_at = datetime.now(UTC)
    report.last_generated_at = generated_at
    report.next_run_at = compute_next_run(report)
    report.generation_status = "idle"
    result = {
        "report_id": report_public_id(report),
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "generated_at": generated_at.isoformat(),
    }
    report.last_run_result = result
    await db.commit()
    await db.refresh(report)
    return result


async def execute_report_generation(report_id: UUID, tenant_id: UUID) -> None:
    from app.db import async_session_factory

    async with async_session_factory() as db:
        report = await get_report_by_id(db, tenant_id, str(report_id))
        if report is None:
            return
        try:
            await run_report(db, report)
        except Exception:
            await db.rollback()
            async with async_session_factory() as err_db:
                failed = await get_report_by_id(err_db, tenant_id, str(report_id))
                if failed is not None:
                    failed.generation_status = "error"
                    await err_db.commit()
