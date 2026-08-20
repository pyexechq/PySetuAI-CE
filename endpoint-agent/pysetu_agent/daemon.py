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
import sys
import time
from datetime import UTC, datetime
from typing import Any

from . import __version__
from .client import ControlPlaneClient, ControlPlaneError
from .config import AgentConfig, missing_fields
from .discovery import DiscoveredMcpServer, DiscoveredTool, discover_mcp_servers, discover_tools
from .enforce import DEFAULT_QUARANTINE_DIR
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


def agent_payload(
    endpoint_id: str,
    tool: DiscoveredTool,
    mcp_servers: list[DiscoveredMcpServer] | None = None,
) -> dict[str, Any]:
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
        "mcp_servers": [server.name for server in (mcp_servers or [])],
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


def mcp_discovery_event_payload(endpoint_id: str, servers: list[DiscoveredMcpServer]) -> dict[str, Any]:
    return {
        "endpoint_id": endpoint_id,
        "source": "endpoint",
        "event_type": "mcp_discovery",
        "action": "mcp.discover",
        "resource": ",".join(sorted({server.name for server in servers})) or "-",
        "classification": ["mcp"],
        "decision": "log",
        "risk_score": 0,
        "metadata": {
            "discovered": [
                {
                    "name": server.name,
                    "source": server.source,
                    "command": server.command,
                    "url": server.url,
                    "transport": server.transport,
                    "tools": list(server.tools),
                }
                for server in servers
            ]
        },
    }


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
    mcp_servers = discover_mcp_servers()
    for tool in tools:
        client.upsert_agent(agent_payload(endpoint_id, tool, mcp_servers))

    client.ingest_event(discovery_event_payload(endpoint_id, tools))
    if mcp_servers:
        client.ingest_event(mcp_discovery_event_payload(endpoint_id, mcp_servers))
    client.heartbeat(endpoint_id, {"status": "online"})

    return {
        "endpoint_id": endpoint_id,
        "discovered_tools": [tool.name for tool in tools],
        "discovered_mcp_servers": [server.name for server in mcp_servers],
    }


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


def load_local_policy(policy_file: str | None) -> LocalPolicy:
    """Load policy from a local cache file, or defaults if none/unreadable."""
    if not policy_file:
        return LocalPolicy.defaults()
    return PolicyCache(policy_file).load_or_defaults()


def run_mcp_gateway(config: AgentConfig, server_name: str | None, policy_file: str | None = None) -> int:
    """Run the stdio MCP gateway.

    With ``server_name``, proxies one discovered server. Without it, runs the
    multiplexer over all discovered stdio servers in a single process.
    """
    from .mcp_gateway import run_gateway, run_multiplex_gateway

    servers = discover_mcp_servers()
    if server_name is None:
        stdio_servers = [s for s in servers if s.transport == "stdio" and s.command]
        if not stdio_servers:
            print("pysetu: no stdio MCP servers discovered to multiplex", file=sys.stderr)
            return 1
        return run_multiplex_gateway(stdio_servers, load_local_policy(policy_file))

    server = next((s for s in servers if s.name == server_name), None)
    if server is None:
        print(f"pysetu: unknown MCP server: {server_name}", file=sys.stderr)
        return 1
    if server.transport != "stdio":
        print(f"pysetu: server {server_name} uses {server.transport}; only stdio is supported", file=sys.stderr)
        return 1
    return run_gateway(server, load_local_policy(policy_file))


def run_mcp_gateway_config(config: AgentConfig, output_path: str | None = None, launcher: str | None = None) -> int:
    """Generate an MCP config pointing tools at the gateway. Writes to output_path or prints."""
    from .mcp_gateway import gateway_config, write_gateway_config

    servers = discover_mcp_servers()
    if output_path and output_path != "-":
        path = write_gateway_config(output_path, servers, launcher=launcher)
        print(f"Wrote MCP gateway config to {path}")
    else:
        print(json.dumps(gateway_config(servers, launcher=launcher), indent=2))
    return 0


def run_scan(
    config: AgentConfig,
    scan_dir: str,
    policy_file: str | None = None,
    *,
    enforce: bool = False,
    quarantine_dir: str | None = None,
) -> dict[str, Any]:
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

    events = scan_directory(scan_dir, policy, enforce=enforce, quarantine_dir=quarantine_dir)
    for event in events:
        client.ingest_event(file_event_payload(endpoint_id, event))

    client.heartbeat(endpoint_id, {"status": "online"})
    return {"endpoint_id": endpoint_id, "events": len(events)}


def run_watch(
    config: AgentConfig,
    watch_dir: str,
    policy_file: str | None = None,
    *,
    enforce: bool = False,
    quarantine_dir: str | None = None,
) -> None:
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

    print(f"Watching {watch_dir} for sensitive file changes...")
    watch_directory(watch_dir, policy, on_events, enforce=enforce, quarantine_dir=quarantine_dir)


def run_wrap_shell(shim_dir: str) -> None:
    """Install PATH shims for wrapped AI binaries and print PATH instructions."""
    from .wrapper import install_shim

    created = install_shim(shim_dir)
    print(f"Installed {len(created)} shim(s) in {shim_dir}:")
    for path in created:
        print(f"  {path}")
    print(f"\nAdd the shim directory to your PATH (e.g. in ~/.zshrc):")
    print(f'  export PATH="{shim_dir}:$PATH"')


def run_clipboard(config: AgentConfig, policy_file: str | None = None) -> None:
    """Run the clipboard DLP monitor loop."""
    from .clipboard import monitor_clipboard

    client = ControlPlaneClient(config.backend_url, config.api_key)
    policy = load_policy(client, policy_file)

    def on_event(decision) -> None:
        print(f"[{datetime.now(UTC).isoformat()}] clipboard {decision.action}: {', '.join(decision.classifications)}")

    print("Monitoring clipboard for sensitive content (Ctrl-C to stop)...")
    monitor_clipboard(policy, on_event=on_event)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PySetu endpoint agent")
    parser.add_argument("--once", action="store_true", help="Run a single registration + discovery pass")
    parser.add_argument("--config", help="Path to a JSON config file")
    parser.add_argument("--scan-dir", help="Scan a directory for secrets/PII and ingest findings")
    parser.add_argument("--watch", help="Watch a directory continuously for sensitive file changes")
    parser.add_argument("--policy-file", help="Path to a local policy cache JSON file")
    parser.add_argument("--enforce", action="store_true", help="Apply redaction/quarantine during scan or watch")
    parser.add_argument("--quarantine-dir", default=DEFAULT_QUARANTINE_DIR, help="Quarantine directory for blocked files")
    parser.add_argument("--wrap-shell", action="store_true", help="Install PATH shims for claude/cursor/code")
    parser.add_argument("--wrap-shell-dir", default=os.path.join(os.path.expanduser("~"), ".pysetu", "bin"), help="Shim directory")
    parser.add_argument("--clipboard", action="store_true", help="Run the clipboard DLP monitor (macOS)")
    parser.add_argument("--mcp-gateway", action="store_true", help="Run the MCP gateway proxy (stdio)")
    parser.add_argument("--server", help="Upstream MCP server name to proxy (with --mcp-gateway)")
    parser.add_argument("--mcp-gateway-config", nargs="?", const="-", metavar="PATH", help="Generate an MCP config pointing tools at the gateway (PATH, or '-' to print)")
    args = parser.parse_args(argv)

    config = AgentConfig.load(args.config)

    # Offline modes that do not require control-plane credentials.
    if args.mcp_gateway_config is not None:
        return run_mcp_gateway_config(config, args.mcp_gateway_config)

    if args.mcp_gateway:
        # Without --server, multiplex all discovered stdio servers in one process.
        return run_mcp_gateway(config, args.server, args.policy_file)

    missing = missing_fields(config)
    if missing:
        print(f"Missing required configuration: {', '.join(missing)}. Set PYSETU_API_KEY and PYSETU_HOSTNAME.")
        return 2

    if args.wrap_shell:
        run_wrap_shell(args.wrap_shell_dir)
        return 0

    if args.clipboard:
        try:
            run_clipboard(config, args.policy_file)
        except ControlPlaneError as exc:
            print(f"Control plane error: {exc}")
            return 1
        return 0

    if args.scan_dir:
        try:
            result = run_scan(config, args.scan_dir, args.policy_file, enforce=args.enforce, quarantine_dir=args.quarantine_dir)
        except ControlPlaneError as exc:
            print(f"Control plane error: {exc}")
            return 1
        print(f"Scanned endpoint {result['endpoint_id']}; emitted {result['events']} finding(s).")
        return 0

    if args.watch:
        try:
            run_watch(config, args.watch, args.policy_file, enforce=args.enforce, quarantine_dir=args.quarantine_dir)
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
