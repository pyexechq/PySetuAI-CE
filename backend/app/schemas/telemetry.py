"""Telemetry facade schemas (BL-076) — single source for Dashboard + Monitoring."""

from __future__ import annotations

from pydantic import BaseModel


class TelemetryActionCount(BaseModel):
    action: str
    count: int


class TelemetryRiskCount(BaseModel):
    risk: str
    count: int


class TelemetryStatusCount(BaseModel):
    status: str
    count: int


class TelemetryTrendPoint(BaseModel):
    date: str
    total: int
    blocked: int


class TelemetryBlockedEvent(BaseModel):
    id: str
    timestamp: str
    actor: str
    action: str
    resource: str
    risk: str
    details: str


class TelemetrySummaryResponse(BaseModel):
    """High-level gateway telemetry summary (dashboard / monitoring header)."""

    generated_at: str
    period_days: int
    total_events: int
    allowed: int
    blocked: int
    under_review: int
    block_rate: float
    avg_latency_ms: int
    p95_latency_ms: int
    total_tokens: int
    total_cost_usd: float
    active_models: int
    by_action: list[TelemetryActionCount]
    by_risk: list[TelemetryRiskCount]
    daily_trend: list[TelemetryTrendPoint]


class TelemetryOperationsResponse(BaseModel):
    """Live operations panel — requests, tokens, p50/p95, blocks (S13-06)."""

    generated_at: str
    requests_total: int
    requests_allowed: int
    requests_blocked: int
    requests_review: int
    tokens_total: int
    prompt_tokens: int
    completion_tokens: int
    p50_latency_ms: int
    p95_latency_ms: int
    block_rate: float
    by_action: list[TelemetryActionCount]
    by_status: list[TelemetryStatusCount]
    recent_blocked: list[TelemetryBlockedEvent]
