"""AI-style summaries and insights for dashboard metric cards."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.dashboard import (
    DashboardMetricInsightResponse,
    DashboardOverviewResponse,
    MetricInsightContextRequest,
)
from app.schemas.openai import ChatMessage
from app.services.ai_assist_config_service import complete_ai_assist, resolve_ai_assist_config
from app.services.dashboard_service import build_dashboard_overview

METRIC_KEYS = frozenset(
    {
        "total_requests",
        "blocked_requests",
        "success_rate",
        "pii_redactions",
        "policy_violations",
        "mcp_violations",
        "agentic_security_events",
        "mcp_tool_chain_events",
        "cost_savings",
        "compliance_score",
        "protocol_translations",
        "provider_migrations",
        "translation_cost_savings",
        "legacy_app_compatibility",
    }
)

METRIC_TITLES: dict[str, str] = {
    "total_requests": "Total AI Requests",
    "blocked_requests": "Blocked Requests",
    "success_rate": "Success Rate",
    "pii_redactions": "PII Redactions",
    "policy_violations": "Policy Violations",
    "mcp_violations": "MCP Violations",
    "agentic_security_events": "Agentic Security Events",
    "mcp_tool_chain_events": "MCP Tool Chain Events",
    "cost_savings": "Total LLM Spend",
    "compliance_score": "Compliance Score",
    "protocol_translations": "Protocol Translations",
    "provider_migrations": "Provider Migrations",
    "translation_cost_savings": "Cost Savings via Translation",
    "legacy_app_compatibility": "Legacy App Compatibility",
}


def _trend_label(change: float, *, invert: bool = False) -> str:
    good = change <= 0 if invert else change >= 0
    direction = "up" if change > 0 else "down" if change < 0 else "flat"
    tone = "positive" if good else "needs attention"
    return f"{direction} {abs(change)}% ({tone})"


def _metric_snapshot(metric_key: str, overview: DashboardOverviewResponse) -> dict:
    m = overview.metrics
    uag = overview.uag
    snapshots: dict[str, dict] = {
        "total_requests": {
            "value": m.total_requests,
            "change_pct": m.total_requests_change_pct,
            "period": m.comparison_period,
        },
        "blocked_requests": {
            "value": m.blocked_requests,
            "change_pct": m.blocked_requests_change_pct,
            "period": m.comparison_period,
            "block_rate": round(m.blocked_requests / m.total_requests * 100, 1) if m.total_requests else 0,
        },
        "success_rate": {
            "value": m.success_rate,
            "change_pts": m.success_rate_change_pts,
            "period": m.comparison_period,
        },
        "pii_redactions": {
            "value": m.pii_redactions,
            "change_pct": m.pii_redactions_change_pct,
            "period": m.comparison_period,
        },
        "policy_violations": {
            "value": m.policy_violations,
            "change_pct": m.policy_violations_change_pct,
            "period": m.comparison_period,
        },
        "mcp_violations": {
            "value": m.mcp_violations,
            "change_pct": m.mcp_violations_change_pct,
            "period": m.comparison_period,
        },
        "agentic_security_events": {
            "value": m.agentic_security_events,
            "change_pct": m.agentic_security_events_change_pct,
            "period": m.comparison_period,
        },
        "mcp_tool_chain_events": {
            "value": m.mcp_tool_chain_events,
            "change_pct": m.mcp_tool_chain_events_change_pct,
            "period": m.comparison_period,
        },
        "cost_savings": {
            "value": m.cost_savings,
            "change_pct": 0,
            "period": m.comparison_period,
        },
        "compliance_score": {
            "value": m.compliance_score,
            "source": "average of live framework control scores",
            "change_pts": m.compliance_score_change_pts,
            "frameworks": [
                {
                    "name": f.name,
                    "score": f.score,
                    "status": f.status,
                    "passed": f.passed,
                    "in_progress": f.in_progress,
                    "not_met": f.not_met,
                }
                for f in overview.compliance_frameworks
            ],
        },
    }
    if uag:
        snapshots.update(
            {
                "protocol_translations": {"value": uag.protocol_translations, "period": "last 30 days"},
                "provider_migrations": {"value": uag.provider_migrations, "period": "active routes"},
                "translation_cost_savings": {"value": uag.cost_savings_usd, "period": "estimated"},
                "legacy_app_compatibility": {"value": uag.legacy_app_compatibility, "period": "success rate"},
            }
        )
    return snapshots.get(metric_key, {"value": 0})


def _resolve_insight_title(metric_key: str, context: MetricInsightContextRequest | None) -> str:
    if context and context.card_title:
        return context.card_title.strip()
    return METRIC_TITLES[metric_key]


def _merge_snapshot(
    metric_key: str,
    overview: DashboardOverviewResponse,
    context: MetricInsightContextRequest | None,
) -> dict:
    snapshot = dict(_metric_snapshot(metric_key, overview))
    if not context:
        return snapshot
    if context.display_value is not None:
        snapshot["card_display_value"] = context.display_value
    if context.card_title:
        snapshot["card_title"] = context.card_title
    if context.period_label:
        snapshot["period"] = context.period_label
    if context.change is not None:
        snapshot["card_change"] = context.change
    return snapshot


def _display_differs_from_baseline(baseline: object | None, display_value: str) -> bool:
    if baseline is None:
        return False
    normalized_display = display_value.replace("%", "").replace(",", "").strip()
    try:
        return abs(float(normalized_display) - float(baseline)) > 0.05
    except ValueError:
        return str(baseline) != normalized_display


def _apply_card_context(
    metric_key: str,
    overview: DashboardOverviewResponse,
    insight: DashboardMetricInsightResponse,
    context: MetricInsightContextRequest | None,
) -> DashboardMetricInsightResponse:
    if not context or not context.display_value:
        return insight

    title = _resolve_insight_title(metric_key, context)
    period = f" ({context.period_label})" if context.period_label else ""
    summary = f"{title} is {context.display_value}{period}."

    baseline = _metric_snapshot(metric_key, overview).get("value")
    insights = list(insight.insights)
    if baseline is not None and _display_differs_from_baseline(baseline, context.display_value):
        insights.insert(
            0,
            f"Tenant dashboard baseline for this metric (last 30 days) is {baseline}; this card may use a different period or view.",
        )

    return insight.model_copy(
        update={
            "title": title,
            "summary": summary,
            "insights": insights[:5],
        }
    )


def _playbook_insight(
    metric_key: str,
    overview: DashboardOverviewResponse,
    context: MetricInsightContextRequest | None = None,
) -> DashboardMetricInsightResponse:
    m = overview.metrics
    uag = overview.uag
    title = METRIC_TITLES[metric_key]
    top_threat = overview.top_threats[0].name if overview.top_threats else "No dominant threat pattern yet"
    top_policy = overview.top_policies[0].name if overview.top_policies else "Prompt Injection Guard"

    playbooks: dict[str, tuple[str, list[str], list[str]]] = {
        "total_requests": (
            f"{m.total_requests:,} governed AI requests were recorded in the last 30 days, "
            f"{_trend_label(m.total_requests_change_pct or 0)} versus the prior period.",
            [
                "Traffic growth usually correlates with new agents, MCP tools, or gateway keys entering production.",
                "Sudden spikes without matching allow events may indicate misconfigured client keys.",
            ],
            [
                "Review top agents in the dashboard table for unexpected volume.",
                "Validate ingress bindings on high-traffic API keys.",
            ],
        ),
        "blocked_requests": (
            f"{m.blocked_requests:,} requests were blocked ({round(m.blocked_requests / m.total_requests * 100, 1) if m.total_requests else 0}% block rate), "
            f"{_trend_label(m.blocked_requests_change_pct or 0, invert=True)}.",
            [
                f"Most recent blocked pattern: {top_threat}.",
                "Blocked events feed Security Center and compliance evidence automatically.",
            ],
            [
                "Inspect Audit Explorer filtered to status=blocked.",
                f"Tighten or test `{top_policy}` rules in Policy Studio.",
            ],
        ),
        "success_rate": (
            f"Success rate is {m.success_rate}% ({_trend_label(m.success_rate_change_pts or 0)} vs prior 30 days).",
            [
                "Success rate reflects traffic that was not blocked after policy, DLP, and ABAC checks (allowed, redacted, or alerted).",
                "Blocking is the platform's protective action; a drop often follows new strict bundles or increased injection attempts.",
            ],
            [
                "Compare weekly traffic chart for correlated block spikes.",
                "Run Governance Sandbox dry-runs before promoting stricter bundles.",
            ],
        ),
        "pii_redactions": (
            f"{m.pii_redactions:,} PII/DLP events were redacted or flagged in the last 30 days.",
            [
                "Redactions indicate sensitive data was detected before or after model calls.",
                "Higher counts are expected when EU/US residency policies are active.",
            ],
            [
                "Open Data Protection to review regional distribution.",
                "Confirm PII Redaction policies match each ingress binding.",
            ],
        ),
        "policy_violations": (
            f"{m.policy_violations:,} policy violations align with blocked governance decisions this period.",
            [
                "Violations include prompt injection, jailbreak, and ABAC blocks.",
                f"Top enforced policy family: {top_policy}.",
            ],
            [
                "Use Compliance Center to map violations to framework controls.",
                "Retest failed prompts in the AI Gateway tester.",
            ],
        ),
        "mcp_violations": (
            f"{m.mcp_violations:,} blocked MCP tool invocations were captured in the last 30 days.",
            [
                "MCP violations are blocked tool calls, not all MCP traffic.",
                "High-risk MCP servers amplify exfiltration and data residency exposure.",
            ],
            [
                "Review MCP Governance trust scores and tool allowlists.",
                "Disable or quarantine servers with elevated risk scores.",
            ],
        ),
        "agentic_security_events": (
            f"{m.agentic_security_events:,} agentic security events were recorded in the last 30 days.",
            [
                "Events span anomalies, exfiltration, prompt-injection findings, and Guardian actions.",
                "A rising count may indicate a new agent or endpoint under active attack.",
            ],
            [
                "Open Agentic Security to triage anomalies and exfiltration.",
                "Review Guardian enforcement actions and adjust response policies.",
            ],
        ),
        "mcp_tool_chain_events": (
            f"{m.mcp_tool_chain_events:,} MCP tool chain events were recorded in the last 30 days.",
            [
                "Tool chain events capture multi-step agent tool calls and their chain risk scores.",
                "High chain risk indicates chained access to sensitive data sources.",
            ],
            [
                "Review MCP Tool Chains for high-risk sequences.",
                "Tighten per-tool policies for chained high-risk tools.",
            ],
        ),
        "cost_savings": (
            "LLM spend tracking is at $0 because provider billing telemetry is not connected for this tenant.",
            [
                "Cost appears when usage-based pricing hooks or provider invoices are integrated.",
                "Translation routing can reduce spend by steering traffic to lower-cost models.",
            ],
            [
                "Configure provider keys in LLM Router or Integrations.",
                "Review Compatibility Center routes for cheaper fallback models.",
            ],
        ),
        "compliance_score": (
            f"Overall compliance score is {m.compliance_score:g}% — the average of "
            f"{len(overview.compliance_frameworks)} live framework scores "
            f"({sum(1 for f in overview.compliance_frameworks if f.status == 'compliant')} compliant).",
            [
                (
                    "At-risk frameworks: "
                    + (
                        ", ".join(f.name for f in overview.compliance_frameworks if f.status == "at-risk")
                        or "none"
                    )
                    + "."
                ),
                (
                    f"Open gaps: {sum((f.not_met or 0) + (f.in_progress or 0) for f in overview.compliance_frameworks)} "
                    "controls are not fully met. This is the same score shown in Compliance Center."
                ),
            ],
            [
                "Open Compliance Center to remediate failing controls.",
                "Export evidence snapshots from Compliance Center → Evidence & exports.",
            ],
        ),
    }

    if uag:
        playbooks.update(
            {
                "protocol_translations": (
                    f"{uag.protocol_translations:,} Universal AI Gateway translations ran in the last 30 days.",
                    [
                        "Translations normalize OpenAI-style calls to Gemini, Claude, Ollama, or Azure routes.",
                        "Failed translations fall back to mock or policy-safe responses.",
                    ],
                    [
                        "Inspect Compatibility Center for route-level error rates.",
                        "Validate translation policies per tenant workload.",
                    ],
                ),
                "provider_migrations": (
                    f"{len(uag.route_breakdown)} active provider migration routes are configured.",
                    [
                        "Each route represents a source protocol mapped to a target provider.",
                        "More routes increase legacy app compatibility but need governance review.",
                    ],
                    [
                        "Simulate translations in Governance Sandbox before production cutover.",
                    ],
                ),
                "translation_cost_savings": (
                    f"Estimated translation savings are ${uag.cost_savings_usd:.2f} based on successful routed calls.",
                    [
                        "Estimate assumes cheaper target models vs. default OpenAI routing.",
                        "Connect billing data for finance-grade chargeback reporting.",
                    ],
                    [
                        "Prioritize high-volume routes in Compatibility Center.",
                    ],
                ),
                "legacy_app_compatibility": (
                    f"Legacy application compatibility success rate is {uag.legacy_app_compatibility}%.",
                    [
                        "Measures successful UAG translations for OpenAI-compatible clients.",
                        "Sub-95% rates suggest mapping or schema gaps on specific routes.",
                    ],
                    [
                        "Review failed translation traces in Audit Explorer.",
                    ],
                ),
            }
        )

    summary, insights, actions = playbooks.get(
        metric_key,
        (f"Summary for {title} is unavailable.", ["No additional context."], ["Refresh dashboard data."]),
    )
    return _apply_card_context(
        metric_key,
        overview,
        DashboardMetricInsightResponse(
            metric_key=metric_key,
            title=_resolve_insight_title(metric_key, context),
            summary=summary,
            insights=insights,
            recommended_actions=actions,
            ai_generated=False,
            generated_at=datetime.now(UTC),
        ),
        context,
    )


def _parse_ai_insights(text: str) -> tuple[str, list[str], list[str]] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    summary = str(payload.get("summary", "")).strip()
    insights = [str(item).strip() for item in payload.get("insights", []) if str(item).strip()]
    actions = [str(item).strip() for item in payload.get("recommended_actions", []) if str(item).strip()]
    if not summary or not insights:
        return None
    return summary, insights[:5], actions[:5]


async def build_metric_insight(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    metric_key: str,
    context: MetricInsightContextRequest | None = None,
) -> DashboardMetricInsightResponse:
    key = metric_key.strip().lower()
    if key not in METRIC_KEYS:
        raise ValueError(f"Unknown metric key '{metric_key}'")

    overview = await build_dashboard_overview(db, tenant_id)
    snapshot = _merge_snapshot(key, overview, context)
    playbook = _playbook_insight(key, overview, context)

    config = await resolve_ai_assist_config(db, tenant_id)
    if not config.available:
        return playbook

    prompt = (
        "You are PySetu AI, an enterprise AI governance analyst. "
        "Return ONLY JSON with keys summary (string), insights (array of 2-3 strings), "
        "recommended_actions (array of 2-3 strings). No markdown.\n\n"
        f"Metric: {_resolve_insight_title(key, context)}\n"
        f"Snapshot: {json.dumps(snapshot)}\n"
        f"Top threats: {[t.name for t in overview.top_threats[:3]]}\n"
        f"Top policies: {[p.name for p in overview.top_policies[:3]]}"
    )
    if context and context.display_value:
        prompt += (
            f"\nThe user clicked the card titled '{context.card_title or METRIC_TITLES[key]}' "
            f"which displays '{context.display_value}'. "
            "Your summary MUST describe this exact card title and value first."
        )
    if key == "compliance_score":
        prompt += (
            "\nThe displayed compliance score is the average of live framework control scores "
            "(GDPR, HIPAA, SOC 2, ISO 27001, NIST AI RMF). Do not treat gateway block rate as the score. "
            "Summary must cite the snapshot value and match Compliance Center."
        )

    try:
        text, ok = await complete_ai_assist(
            config,
            [ChatMessage(role="user", content=prompt)],
            temperature=0.3,
        )
        if ok and text:
            parsed = _parse_ai_insights(text)
            if parsed:
                summary, insights, actions = parsed
                return _apply_card_context(
                    key,
                    overview,
                    DashboardMetricInsightResponse(
                        metric_key=key,
                        title=_resolve_insight_title(key, context),
                        summary=summary,
                        insights=insights,
                        recommended_actions=actions,
                        ai_generated=True,
                        generated_at=datetime.now(UTC),
                    ),
                    context,
                )
    except Exception:
        pass

    return playbook
