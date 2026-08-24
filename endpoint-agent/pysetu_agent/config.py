"""Configuration for the PySetu endpoint agent.

Configuration is read from environment variables and an optional JSON file.
Precedence: explicit environment variables > JSON file > defaults.
"""

from __future__ import annotations

import dataclasses
import json
import os
import socket
from dataclasses import dataclass, field

DEFAULT_BACKEND_URL = "http://localhost:8001"
DEFAULT_POLL_INTERVAL_SECONDS = 300


@dataclass
class AgentConfig:
    backend_url: str = DEFAULT_BACKEND_URL
    api_key: str = ""
    hostname: str = ""
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS
    telemetry_file: str = "pysetu-agent-telemetry.jsonl"

    @classmethod
    def load(cls, config_path: str | None = None, env: dict[str, str] | None = None) -> "AgentConfig":
        env = env if env is not None else dict(os.environ)

        file_values: dict[str, str] = {}
        path = config_path or env.get("PYSETU_CONFIG_FILE")
        if path and os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                file_values = {key: value for key, value in loaded.items() if isinstance(value, (str, int))}

        def pick(env_key: str, file_key: str, default: str) -> str:
            return env.get(env_key) or str(file_values.get(file_key, default))

        backend_url = pick("PYSETU_BACKEND_URL", "backend_url", DEFAULT_BACKEND_URL).rstrip("/")
        hostname = env.get("PYSETU_HOSTNAME") or str(file_values.get("hostname") or "") or socket.gethostname()
        try:
            poll_interval = int(env.get("PYSETU_POLL_INTERVAL") or file_values.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS))
        except (TypeError, ValueError):
            poll_interval = DEFAULT_POLL_INTERVAL_SECONDS

        return cls(
            backend_url=backend_url,
            api_key=env.get("PYSETU_API_KEY") or str(file_values.get("api_key") or ""),
            hostname=hostname,
            poll_interval_seconds=max(5, poll_interval),
            telemetry_file=env.get("PYSETU_TELEMETRY_FILE") or str(file_values.get("telemetry_file") or "pysetu-agent-telemetry.jsonl"),
        )


def missing_fields(config: AgentConfig) -> list[str]:
    return [name for name in ("api_key", "hostname") if not getattr(config, name)]
