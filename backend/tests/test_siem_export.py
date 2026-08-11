import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.services.siem_export_service import audit_log_to_dict, format_cef, format_elastic_ndjson, format_ndjson


def _sample_log(**overrides):
    base = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "timestamp": datetime(2026, 8, 10, 12, 0, 0, tzinfo=UTC),
        "actor": "admin@acme.com",
        "action": "gateway.request",
        "resource": "gpt-4",
        "status": "allowed",
        "risk": "low",
        "details": "Test request",
        "source": "internal",
        "external_id": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_audit_log_to_dict_includes_source_fields() -> None:
    log = _sample_log(source="splunk", external_id="evt-1")
    payload = audit_log_to_dict(log)
    assert payload["source"] == "splunk"
    assert payload["external_id"] == "evt-1"
    assert payload["action"] == "gateway.request"


def test_format_ndjson_one_line_per_event() -> None:
    logs = [_sample_log(), _sample_log(action="policy.block")]
    lines = format_ndjson(logs).splitlines()
    assert len(lines) == 2
    assert "policy.block" in lines[1]


def test_format_cef_contains_action_and_vendor() -> None:
    line = format_cef(_sample_log(action="Login", risk="high"))
    assert line.startswith("CEF:0|PySetu|AI Gateway|")
    assert "Login" in line
    assert "cs2=high" in line


def test_format_elastic_bulk_pairs_index_and_doc() -> None:
    body = format_elastic_ndjson([_sample_log()])
    lines = body.strip().splitlines()
    assert len(lines) == 2
    assert '"index"' in lines[0]
    assert '"actor"' in lines[1]
