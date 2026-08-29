import pytest
from app.schemas.platform import (
    ContainerHealthItem,
    ContainerHealthResponse,
    MarketingLeadItem,
    MarketingPageTraffic,
    MarketingChannelTraffic,
    PlatformMarketingAnalyticsResponse,
)


def test_container_health_schemas():
    item = ContainerHealthItem(
        name="pysetu_backend",
        service="backend",
        status="healthy",
        image="python:3.12-slim",
        role="Core AI Gateway & Control Plane API",
        port="8001:8001",
        uptime="100%",
        latency_ms=4,
        details="FastAPI ASGI Gateway with real-time DLP",
    )
    assert item.name == "pysetu_backend"
    assert item.status == "healthy"
    assert item.latency_ms == 4

    resp = ContainerHealthResponse(
        generated_at="2026-08-25T12:00:00Z",
        overall_status="healthy",
        total_containers=1,
        healthy_count=1,
        containers=[item],
    )
    assert resp.overall_status == "healthy"
    assert resp.total_containers == 1
    assert resp.healthy_count == 1


def test_marketing_analytics_schemas():
    lead = MarketingLeadItem(
        id="lead-123",
        full_name="Sarah Connor",
        work_email="sconnor@cyberdyne.com",
        company_name="Cyberdyne Systems",
        team_size="50-100",
        use_case="Agentic Security & DLP",
        message="Evaluating for enterprise deployment",
        status="pending",
        created_at="2026-08-25T12:00:00Z",
    )
    assert lead.full_name == "Sarah Connor"
    assert lead.status == "pending"

    page = MarketingPageTraffic(
        path="/agentic-security",
        title="Agentic Security",
        views=8920,
        unique_visitors=5620,
        conversion_rate_pct=6.2,
    )
    assert page.views == 8920

    channel = MarketingChannelTraffic(
        channel="LinkedIn",
        visitors=8650,
        percentage=26.8,
    )
    assert channel.percentage == 26.8

    analytics = PlatformMarketingAnalyticsResponse(
        generated_at="2026-08-25T12:00:00Z",
        period_days=30,
        summary={
            "total_pageviews_30d": 51600,
            "unique_visitors_30d": 32220,
            "sandbox_launches": 3480,
            "whitepaper_downloads": 1840,
            "total_leads": 1,
            "pending_leads": 1,
            "trial_conversion_rate_pct": 5.7,
            "avg_session_duration": "3m 42s",
            "bounce_rate_pct": 28.4,
        },
        top_pages=[page],
        channels=[channel],
        recent_leads=[lead],
    )
    assert analytics.period_days == 30
    assert analytics.summary["total_pageviews_30d"] == 51600
    assert len(analytics.recent_leads) == 1
