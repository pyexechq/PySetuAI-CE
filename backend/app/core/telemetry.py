"""OpenTelemetry setup for PySetu API."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.config import settings

_tracer: trace.Tracer | None = None
_initialized = False


def setup_telemetry(app) -> None:
    global _tracer, _initialized
    if _initialized or not settings.otel_enabled:
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": settings.app_version,
        }
    )
    provider = TracerProvider(resource=resource)

    if settings.otel_exporter == "otlp" and settings.otel_otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=settings.otel_otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except Exception as exc:
            print(f"OTLP exporter unavailable, falling back to console: {exc}")
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, excluded_urls="/health,/")
    _tracer = trace.get_tracer(settings.otel_service_name)
    _initialized = True


def get_tracer(name: str) -> trace.Tracer:
    if _tracer is None:
        return trace.get_tracer(name)
    return trace.get_tracer(name)


def current_trace_id() -> str | None:
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx or not ctx.is_valid:
        return None
    return format(ctx.trace_id, "032x")
