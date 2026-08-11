"""AI-style summaries and insights for dashboard metric cards."""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.dashboard import DashboardMetricInsightResponse, DashboardOverviewResponse
from app.schemas.openai import ChatMessage
from app.services.dashboard_service import build_dashboard_overview
from app.services.gemini_client import GeminiError, call_gemini
from app.services.integration_service import resolve_gateway_config

METRIC_KEYS = frozenset(
    {
        "total_requests",
        "blocked_requests",
        "success_rate",
        "pii_redactions",
        "policy_violations",
        "mcp_violations",
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
        "cost_savings": {
            "value": m.cost_savings,
            "change_pct": 0,
            "period": m.comparison_period,
        },
        "compliance_score": {
            "value": m.compliance_score,
            "change_pts": m.compliance_score_change_pts,
            "period": m.comparison_period,
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


def _playbook_insight(metric_key: str, overview: DashboardOverviewResponse) -> DashboardMetricInsightResponse:
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
                "Success rate reflects allowed LLM and MCP traffic after policy, DLP, and ABAC checks.",
                "A drop often follows new strict bundles or increased injection attempts.",
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
            f"{m.mcp_violations:,} MCP-related audit events were captured in the last 30 days.",
            [
                "MCP violations include risky tool calls and offline/degraded servers.",
                "High-risk MCP servers amplify exfiltration and data residency exposure.",
            ],
            [
                "Review MCP Governance trust scores and tool allowlists.",
                "Disable or quarantine servers with elevated risk scores.",
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
            f"Composite compliance posture is {m.compliance_score}% ({_trend_label(m.compliance_score_change_pts or 0)}).",
            [
                "Score blends block rate, PII handling, and live framework control status.",
                f"{len(overview.compliance_frameworks)} frameworks are monitored on this dashboard.",
            ],
            [
                "Open Compliance Center to re-evaluate failing controls.",
                "Export audit evidence from Reports for auditor review.",
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
    return DashboardMetricInsightResponse(
        metric_key=metric_key,
        title=title,
        summary=summary,
        insights=insights,
        recommended_actions=actions,
        ai_generated=False,
        generated_at=datetime.now(UTC),
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
) -> DashboardMetricInsightResponse:
    key = metric_key.strip().lower()
    if key not in METRIC_KEYS:
        raise ValueError(f"Unknown metric key '{metric_key}'")

    overview = await build_dashboard_overview(db, tenant_id)
    snapshot = _metric_snapshot(key, overview)
    playbook = _playbook_insight(key, overview)

    config = await resolve_gateway_config(db, tenant_id)
    if not config.gemini_api_key:
        return playbook

    prompt = (
        "You are HelixGuard AI, an enterprise AI governance analyst. "
        "Return ONLY JSON with keys summary (string), insights (array of 2-3 strings), "
        "recommended_actions (array of 2-3 strings). No markdown.\n\n"
        f"Metric: {METRIC_TITLES[key]}\n"
        f"Snapshot: {json.dumps(snapshot)}\n"
        f"Top threats: {[t.name for t in overview.top_threats[:3]]}\n"
        f"Top policies: {[p.name for p in overview.top_policies[:3]]}"
    )

    try:
        text, _ = await call_gemini(
            config.gemini_default_model,
            [ChatMessage(role="user", content=prompt)],
            config.gemini_api_key,
        )
        parsed = _parse_ai_insights(text)
        if parsed:
            summary, insights, actions = parsed
            return DashboardMetricInsightResponse(
                metric_key=key,
                title=METRIC_TITLES[key],
                summary=summary,
                insights=insights,
                recommended_actions=actions,
                ai_generated=True,
                generated_at=datetime.now(UTC),
            )
    except GeminiError:
        pass

    return playbook
