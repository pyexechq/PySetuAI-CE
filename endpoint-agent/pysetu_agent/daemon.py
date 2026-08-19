"""Daemon entry point: register, discover, and report telemetry.

Run a single pass with ``--once`` (useful for cron and tests) or loop forever
with the configured poll interval.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import socket
import time
from datetime import UTC, datetime
from typing import Any

from . import __version__
from .client import ControlPlaneClient, ControlPlaneError
from .config import AgentConfig, missing_fields
from .discovery import DiscoveredTool, discover_tools
from .policy import LocalPolicy, PolicyCache, policy_from_payload
from .scan import FileScanEvent, scan_directory
from .watcher import watch_directory


def system_info() -> dict[str, str]:
    return {
        "os_name": platform.system() or "unknown",
        "os_version": platform.release() or "",
        "agent_version": __version__,
        "hostname": socket.gethostname(),
    }


def agent_payload(endpoint_id: str, tool: DiscoveredTool) -> dict[str, Any]:
    return {
        "endpoint_id": endpoint_id,
        "name": tool.name,
        "agent_type": tool.agent_type,
        "vendor": tool.vendor,
        "version": tool.version,
        "user_name": os.environ.get("USER") or os.environ.get("USERNAME") or "",
        "status": "active",
        "data_sources": [],
        "tools": [],
        "mcp_servers": [],
        "permissions": [],
    }


def discovery_event_payload(endpoint_id: str, tools: list[DiscoveredTool]) -> dict[str, Any]:
    return {
        "endpoint_id": endpoint_id,
        "source": "endpoint",
        "event_type": "discovery",
        "action": "tool.discover",
        "resource": ",".join(sorted({tool.name for tool in tools})) or "-",
        "classification": [],
        "decision": "log",
        "risk_score": 0,
        "metadata": {
            "discovered": [
                {"name": tool.name, "agent_type": tool.agent_type, "vendor": tool.vendor, "source": tool.source}
                for tool in tools
            ]
        },
    }


def queue_telemetry(config: AgentConfig, event: dict[str, Any]) -> None:
    """Append an event to the local JSONL buffer for offline sync."""
    try:
        with open(config.telemetry_file, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"timestamp": datetime.now(UTC).isoformat(), **event}) + "\n")
    except OSError:
        pass


def run_once(config: AgentConfig) -> dict[str, Any]:
    client = ControlPlaneClient(config.backend_url, config.api_key)

    info = system_info()
    endpoint = client.register_endpoint(
        {
            "hostname": config.hostname,
            "os_name": info["os_name"],
            "os_version": info["os_version"],
            "agent_version": info["agent_version"],
            "metadata": {"first_seen_from": "endpoint-agent"},
        }
    )
    endpoint_id = str(endpoint["id"])

    tools = discover_tools()
    for tool in tools:
        client.upsert_agent(agent_payload(endpoint_id, tool))

    client.ingest_event(discovery_event_payload(endpoint_id, tools))
    client.heartbeat(endpoint_id, {"status": "online"})

    return {"endpoint_id": endpoint_id, "discovered_tools": [tool.name for tool in tools]}


def risk_for_decision(decision: str) -> int:
    return {"block": 90, "approval": 70, "redact": 50, "log": 20, "allow": 0}.get(decision, 20)


def api_decision(decision: str) -> str:
    """Translate local policy actions to the control-plane event vocabulary."""
    return {
        "allow": "allowed",
        "block": "blocked",
        "redact": "redacted",
        "approval": "approval",
        "log": "log",
    }.get(decision, "log")


def file_event_payload(endpoint_id: str, event: FileScanEvent) -> dict[str, Any]:
    return {
        "endpoint_id": endpoint_id,
        "source": "endpoint",
        "event_type": "file",
        "action": "file.read",
        "resource": event.path,
        "classification": event.classifications,
        "decision": api_decision(event.decision),
        "risk_score": risk_for_decision(event.decision),
        "metadata": {"match_count": event.match_count},
    }


def load_policy(client: ControlPlaneClient, policy_file: str | None) -> LocalPolicy:
    if not policy_file:
        return LocalPolicy.defaults()
    cache = PolicyCache(policy_file)
    try:
        policy = policy_from_payload(client.get_policy())
        cache.save(policy)
    except ControlPlaneError:
        policy = cache.load_or_defaults()
    return policy


def run_scan(config: AgentConfig, scan_dir: str, policy_file: str | None = None) -> dict[str, Any]:
    client = ControlPlaneClient(config.backend_url, config.api_key)
    policy = load_policy(client, policy_file)

    info = system_info()
    endpoint = client.register_endpoint(
        {
            "hostname": config.hostname,
            "os_name": info["os_name"],
            "os_version": info["os_version"],
            "agent_version": info["agent_version"],
            "metadata": {"first_seen_from": "endpoint-agent"},
        }
    )
    endpoint_id = str(endpoint["id"])

    events = scan_directory(scan_dir, policy)
    for event in events:
        client.ingest_event(file_event_payload(endpoint_id, event))

    client.heartbeat(endpoint_id, {"status": "online"})
    return {"endpoint_id": endpoint_id, "events": len(events)}


def run_watch(config: AgentConfig, watch_dir: str, policy_file: str | None = None) -> None:
    client = ControlPlaneClient(config.backend_url, config.api_key)
    policy = load_policy(client, policy_file)

    info = system_info()
    endpoint = client.register_endpoint(
        {
            "hostname": config.hostname,
            "os_name": info["os_name"],
            "os_version": info["os_version"],
            "agent_version": info["agent_version"],
            "metadata": {"first_seen_from": "endpoint-agent"},
        }
    )
    endpoint_id = str(endpoint["id"])
    client.ingest_event(discovery_event_payload(endpoint_id, []))
    client.heartbeat(endpoint_id, {"status": "online"})

    def on_events(events: list[FileScanEvent]) -> None:
        for event in events:
            try:
                client.ingest_event(file_event_payload(endpoint_id, event))
                print(f"[{datetime.now(UTC).isoformat()}] {event.decision}: {event.path}")
            except ControlPlaneError as exc:
                print(f"[{datetime.now(UTC).isoformat()}] control plane unavailable: {exc}")

    print(f"Watching {watch_dir} for sensitive file changes…")
    watch_directory(watch_dir, policy, on_events)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PySetu endpoint agent")
    parser.add_argument("--once", action="store_true", help="Run a single registration + discovery pass")
    parser.add_argument("--config", help="Path to a JSON config file")
    parser.add_argument("--scan-dir", help="Scan a directory for secrets/PII and ingest findings")
    parser.add_argument("--watch", help="Watch a directory continuously for sensitive file changes")
    parser.add_argument("--policy-file", help="Path to a local policy cache JSON file")
    args = parser.parse_args(argv)

    config = AgentConfig.load(args.config)
    missing = missing_fields(config)
    if missing:
        print(f"Missing required configuration: {', '.join(missing)}. Set PYSETU_API_KEY and PYSETU_HOSTNAME.")
        return 2

    if args.scan_dir:
        try:
            result = run_scan(config, args.scan_dir, args.policy_file)
        except ControlPlaneError as exc:
            print(f"Control plane error: {exc}")
            return 1
        print(f"Scanned endpoint {result['endpoint_id']}; emitted {result['events']} finding(s).")
        return 0

    if args.watch:
        try:
            run_watch(config, args.watch, args.policy_file)
        except ControlPlaneError as exc:
            print(f"Control plane error: {exc}")
            return 1
        return 0

    if args.once:
        try:
            result = run_once(config)
        except ControlPlaneError as exc:
            print(f"Control plane error: {exc}")
            return 1
        print(f"Registered endpoint {result['endpoint_id']}; discovered: {', '.join(result['discovered_tools']) or 'none'}")
        return 0

    print(f"PySetu endpoint agent v{__version__} starting for {config.hostname}")
    while True:
        try:
            result = run_once(config)
            print(f"[{datetime.now(UTC).isoformat()}] heartbeat ok; agents: {', '.join(result['discovered_tools']) or 'none'}")
        except ControlPlaneError as exc:
            print(f"[{datetime.now(UTC).isoformat()}] control plane unavailable: {exc}")
        time.sleep(config.poll_interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
