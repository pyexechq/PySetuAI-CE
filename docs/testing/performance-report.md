# PySetu AI — Performance Report

**Test Cycle:** QA-001  
**Date:** Aug 11, 2026  
**Environment:** Local (Windows 10, no Docker Compose running during test)  
**Executed By:** Principal QA & Validation Agent

---

## Performance Targets

| Metric | Target | Measured | Status |
|--------|--------|----------|--------|
| Dashboard load | < 2 sec | Not measured | **Not tested** |
| API response (p95) | < 500 ms | Not measured | **Not tested** |
| Policy evaluation | < 100 ms | Not measured | **Not tested** |
| Audit search | < 2 sec | Not measured | **Not tested** |
| Backend unit tests (44) | — | 2.03 sec | Informational |
| Frontend production build | — | 42.2 sec | Informational |

---

## Test Execution Notes

Performance testing was **not executed** in Cycle QA-001 because:

1. Docker Compose services (PostgreSQL, Redis, backend API) were not running during the test session
2. No k6 or locust performance suite exists in the repository
3. No Playwright performance tracing is configured
4. Performance testing requires a dedicated test environment with seeded data at scale

---

## Observations from Code Review

### Potential Performance Concerns

| Area | Observation | Risk |
|------|-------------|------|
| Audit Explorer live polling | Frontend polls `/audit/logs` every 3 seconds | Medium — unnecessary load at scale; should use WebSocket or SSE |
| Dashboard overview | Single endpoint aggregates KPIs, trends, charts | Low — efficient if query is optimized |
| Policy engine | In-process regex/keyword evaluation | Low — should meet 100ms target for typical rule sets |
| Gateway chat | Policy inspect → DLP → route → upstream → audit | Medium — latency depends on upstream LLM; PySetu overhead should be measured separately |
| Celery tasks | Reports, audit ingest, SIEM export, rebalance | Low — async, non-blocking |
| Audit log table | No pagination limit documented in API | Medium — large tenants may return slow queries |
| MCP tool discovery | JSON-RPC session per server | Low — admin operation, not hot path |

### Positive Indicators

- Async SQLAlchemy 2.0 with connection pooling
- Redis for rate limiting and OIDC state (not DB round-trips)
- Celery for heavy async work (audit ingest batches, report generation)
- OpenTelemetry instrumentation available for latency tracing
- TanStack Query on frontend with caching

---

## Recommended Performance Test Plan (QA-002+)

### Phase 1 — Baseline (Sprint 7)

| Test | Tool | Data | Target |
|------|------|------|--------|
| Health check latency | k6 | 1 VU, 100 iterations | p95 < 50ms |
| Login latency | k6 | 1 VU, 50 iterations | p95 < 500ms |
| Dashboard overview | k6 | 1 VU, 50 iterations | p95 < 2000ms |
| Policy evaluation (unit benchmark) | pytest-benchmark | 100 rules | p95 < 100ms |
| Audit log search (1000 records) | k6 | 1 VU, 50 iterations | p95 < 2000ms |

### Phase 2 — Load (Sprint 8)

| Test | Tool | Load | Target |
|------|------|------|--------|
| Concurrent logins | k6 | 50 VU, 5 min | p95 < 500ms, 0 errors |
| Gateway chat completions | k6 | 20 VU, 5 min | p95 < 500ms (PySetu overhead only, mock mode) |
| Audit ingest batch | k6 | 10 VU, 100 events each | p95 < 1000ms |
| Dashboard under load | k6 | 30 VU, 5 min | p95 < 2000ms |

### Phase 3 — Stress (Sprint 9)

| Test | Tool | Load | Target |
|------|------|------|--------|
| Rate limit verification | k6 | 100 login attempts/min | 429 after threshold |
| Large tenant audit search | k6 | 100K audit records | p95 < 2000ms |
| Policy engine with 500 rules | pytest-benchmark | 500 rules | p95 < 100ms |

---

## Performance Approval Status

| Gate | Status |
|------|--------|
| Dashboard < 2 sec | **Not tested** |
| API < 500 ms | **Not tested** |
| Policy eval < 100 ms | **Not tested** |
| Search < 2 sec | **Not tested** |

**Performance approval: NOT EVALUATED — deferred to QA-002.**

No performance regressions can be reported without a baseline measurement.
