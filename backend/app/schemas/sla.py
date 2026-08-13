from pydantic import BaseModel


class GatewaySlaResponse(BaseModel):
    generated_at: str
    period_days: int
    requests_total: int
    successful_requests: int
    failed_requests: int
    availability_percent: float
    error_rate_percent: float
    p50_latency_ms: int
    p95_latency_ms: int
    p99_latency_ms: int
    average_gateway_overhead_ms: int
    providers_active: int
    pooling_instrumented: bool
    pool_reuse_rate_percent: float | None
    pool_note: str