"""Format and serialize audit logs for external SIEM platforms."""

from __future__ import annotations

import json
from typing import Any

from app.models.governance import AuditLog

CEF_VERSION = 0
CEF_DEVICE_VENDOR = "PySetu"
CEF_DEVICE_PRODUCT = "AI Gateway"
CEF_DEVICE_VERSION = "0.1.0"


def audit_log_to_dict(log: AuditLog) -> dict[str, Any]:
    return {
        "id": str(log.id),
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        "tenant_id": str(log.tenant_id),
        "actor": log.actor,
        "action": log.action,
        "resource": log.resource,
        "status": log.status,
        "risk": log.risk,
        "details": log.details,
        "source": log.source,
        "external_id": log.external_id,
    }


def _cef_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("=", "\\=").replace("\n", " ")


def format_cef(log: AuditLog) -> str:
    severity_map = {"low": 3, "medium": 5, "high": 8, "critical": 10}
    severity = severity_map.get(log.risk.lower(), 3)
    extension = " ".join(
        [
            f"src={_cef_escape(log.actor)}",
            f"act={_cef_escape(log.action)}",
            f"destinationServiceName={_cef_escape(log.resource)}",
            f"cs1={_cef_escape(log.status)}",
            "cs1Label=Status",
            f"cs2={_cef_escape(log.risk)}",
            "cs2Label=Risk",
            f"cs3={_cef_escape(log.source)}",
            "cs3Label=Source",
            f"msg={_cef_escape(log.details[:512])}",
        ]
    )
    return (
        f"CEF:{CEF_VERSION}|{_cef_escape(CEF_DEVICE_VENDOR)}|{_cef_escape(CEF_DEVICE_PRODUCT)}|"
        f"{_cef_escape(CEF_DEVICE_VERSION)}|{_cef_escape(log.action)}|{_cef_escape(log.action)}|{severity}|{extension}"
    )


def format_ndjson(logs: list[AuditLog]) -> str:
    return "\n".join(json.dumps(audit_log_to_dict(log), separators=(",", ":")) for log in logs)


def format_cef_lines(logs: list[AuditLog]) -> str:
    return "\n".join(format_cef(log) for log in logs)


def format_json_array(logs: list[AuditLog]) -> str:
    return json.dumps([audit_log_to_dict(log) for log in logs], indent=2)


def format_elastic_ndjson(logs: list[AuditLog], index: str = "pysetu-audit") -> str:
    lines: list[str] = []
    for log in logs:
        meta = json.dumps({"index": {"_index": index, "_id": str(log.id)}})
        doc = json.dumps(audit_log_to_dict(log), separators=(",", ":"))
        lines.append(meta)
        lines.append(doc)
    return "\n".join(lines) + ("\n" if lines else "")
