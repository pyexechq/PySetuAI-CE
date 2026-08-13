"""Trace id extraction from audit log details."""

from __future__ import annotations

import uuid


def extract_trace_id(details: str | None, log_id: uuid.UUID | str) -> str:
    """Pull OpenTelemetry trace id from audit details regardless of field order."""
    text = details or ""
    marker = "trace_id="
    if marker in text:
        fragment = text.split(marker, 1)[1]
        trace_id = fragment.split(";", 1)[0].strip()
        if trace_id:
            return trace_id
    return f"trace-{str(log_id)[:8]}"
