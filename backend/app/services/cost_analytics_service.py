"""Per-user / team / model token and cost analytics from audit usage_metadata (BL-072)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import AuditLog
from app.services.compounding_cost_service import DEFAULT_COST_PER_1K, _model_rate, _usd


def _empty_bucket(key: str, label: str) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "requests": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost_usd": 0.0,
    }


def _accumulate(bucket: dict[str, Any], meta: dict[str, Any], *, cost_per_1k: float) -> None:
    tokens = int(meta.get("total_tokens") or 0)
    prompt = int(meta.get("prompt_tokens") or 0)
    completion = int(meta.get("completion_tokens") or 0)
    model = str(meta.get("model") or "unknown")
    cost = _usd(tokens, _model_rate(model, cost_per_1k))
    bucket["requests"] += 1
    bucket["prompt_tokens"] += prompt
    bucket["completion_tokens"] += completion
    bucket["total_tokens"] += tokens
    bucket["cost_usd"] = round(bucket["cost_usd"] + cost, 4)


def _user_label(meta: dict[str, Any], actor: str) -> tuple[str, str]:
    end_user = str(meta.get("end_user") or "").strip()
    user_id = str(meta.get("user_id") or "").strip()
    if end_user:
        return f"user:{end_user}", end_user
    if user_id:
        return f"id:{user_id}", f"User {user_id[:8]}"
    actor_label = (actor or "unknown").strip()
    return f"actor:{actor_label}", actor_label


def _team_label(meta: dict[str, Any]) -> tuple[str, str]:
    key_name = str(meta.get("client_api_key_name") or "").strip()
    key_id = str(meta.get("client_api_key_id") or "").strip()
    if key_name:
        return f"key:{key_id or key_name}", key_name
    if meta.get("auth_type") == "jwt":
        return "jwt", "JWT users"
    return "unattributed", "Unattributed"


def summarize_usage_rows(
    rows: list[tuple[dict | None, datetime | None, str | None]],
    *,
    cost_per_1k: float = DEFAULT_COST_PER_1K,
    period_days: int = 30,
) -> dict[str, Any]:
    by_model: dict[str, dict[str, Any]] = {}
    by_user: dict[str, dict[str, Any]] = {}
    by_team: dict[str, dict[str, Any]] = {}
    daily: dict[str, dict[str, Any]] = {}

    total_requests = 0
    total_tokens = 0
    total_cost = 0.0

    for meta_raw, timestamp, actor in rows:
        if not isinstance(meta_raw, dict):
            continue
        total_requests += 1
        model = str(meta_raw.get("model") or "unknown")
        if model not in by_model:
            by_model[model] = _empty_bucket(model, model)
        _accumulate(by_model[model], meta_raw, cost_per_1k=cost_per_1k)

        user_key, user_label = _user_label(meta_raw, actor or "")
        if user_key not in by_user:
            by_user[user_key] = _empty_bucket(user_key, user_label)
        _accumulate(by_user[user_key], meta_raw, cost_per_1k=cost_per_1k)

        team_key, team_label = _team_label(meta_raw)
        if team_key not in by_team:
            by_team[team_key] = _empty_bucket(team_key, team_label)
        _accumulate(by_team[team_key], meta_raw, cost_per_1k=cost_per_1k)

        tokens = int(meta_raw.get("total_tokens") or 0)
        total_tokens += tokens
        total_cost += _usd(tokens, _model_rate(model, cost_per_1k))

        if timestamp is not None:
            day = timestamp.astimezone(UTC).date().isoformat()
            if day not in daily:
                daily[day] = {"date": day, "requests": 0, "total_tokens": 0, "cost_usd": 0.0}
            daily[day]["requests"] += 1
            daily[day]["total_tokens"] += tokens
            daily[day]["cost_usd"] = round(daily[day]["cost_usd"] + _usd(tokens, _model_rate(model, cost_per_1k)), 4)

    def _sorted_buckets(buckets: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(buckets.values(), key=lambda item: item["cost_usd"], reverse=True)

    daily_trend = sorted(daily.values(), key=lambda item: item["date"])

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "period_days": period_days,
        "summary": {
            "requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 4),
            "avg_cost_per_request_usd": round(total_cost / total_requests, 4) if total_requests else 0.0,
            "avg_tokens_per_request": round(total_tokens / total_requests, 1) if total_requests else 0.0,
        },
        "by_model": _sorted_buckets(by_model),
        "by_user": _sorted_buckets(by_user),
        "by_team": _sorted_buckets(by_team),
        "daily_trend": daily_trend,
    }


async def build_cost_analytics(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    days: int = 30,
    cost_per_1k: float = DEFAULT_COST_PER_1K,
) -> dict[str, Any]:
    period_days = max(1, min(days, 90))
    since = datetime.now(UTC) - timedelta(days=period_days)
    result = await db.execute(
        select(AuditLog.usage_metadata, AuditLog.timestamp, AuditLog.actor).where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.action == "LLM Request",
            AuditLog.timestamp >= since,
            AuditLog.usage_metadata.is_not(None),
        )
    )
    rows = [(row[0], row[1], row[2]) for row in result.all()]
    return summarize_usage_rows(rows, cost_per_1k=cost_per_1k, period_days=period_days)


def llm_usage_items_from_models(by_model: list[dict[str, Any]], total_tokens: int) -> list[dict[str, Any]]:
    """Map model buckets to dashboard LLM usage chart rows."""
    if not by_model:
        return []
    items: list[dict[str, Any]] = []
    for bucket in by_model:
        share = (bucket["total_tokens"] / total_tokens * 100) if total_tokens else 0.0
        avg = bucket["total_tokens"] / bucket["requests"] if bucket["requests"] else 0.0
        items.append(
            {
                "model": bucket["label"],
                "percentage": round(share, 1),
                "requests": bucket["requests"],
                "total_tokens": bucket["total_tokens"],
                "avg_tokens_per_request": round(avg, 1),
                "cost_usd": bucket["cost_usd"],
            }
        )
    return items
