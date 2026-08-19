"""Minimal stdlib HTTP client for the PySetu control plane."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

API_PREFIX = "/api/v1"


class ControlPlaneError(RuntimeError):
    """Raised when the control plane rejects or cannot be reached."""


class ControlPlaneClient:
    def __init__(self, backend_url: str, api_key: str, timeout: int = 15) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.backend_url}{API_PREFIX}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ControlPlaneError(f"{method} {path} failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise ControlPlaneError(f"{method} {path} unreachable: {exc.reason}") from exc

    def register_endpoint(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/endpoints", payload)

    def heartbeat(self, endpoint_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"/endpoints/{endpoint_id}/heartbeat", payload)

    def upsert_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/agents", payload)

    def ingest_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/security-events/ingest", payload)

    def get_policy(self) -> dict[str, Any]:
        return self._request("GET", "/agentic/policy")
