from app.services.sla_service import percentile, summarize_sla


def test_percentile_and_sla_summary() -> None:
    assert percentile([100, 200, 300, 400], 0.95) == 400
    result = summarize_sla(
        [
            ("allowed", {"latency_ms": 100, "gateway_overhead_ms": 8}),
            ("allowed", {"latency_ms": 200, "gateway_overhead_ms": 12}),
            ("error", {"latency_ms": 900, "gateway_overhead_ms": 20}),
        ],
        provider_count=2,
        period_days=7,
    )

    assert result["requests_total"] == 3
    assert result["failed_requests"] == 1
    assert result["availability_percent"] == 66.67
    assert result["p99_latency_ms"] == 900
    assert result["average_gateway_overhead_ms"] == 13
    assert result["pooling_instrumented"] is False