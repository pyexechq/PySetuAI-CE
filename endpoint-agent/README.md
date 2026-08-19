# PySetu Endpoint Agent

Lightweight discovery + telemetry daemon for the PySetu AI Control Plane.
Phase 1 scope: register the endpoint, heartbeat, discover installed AI tools, and
ingest discovery events. Enforcement (file/shell/MCP) is a later phase.

Standard library only — no third-party runtime dependencies.

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `PYSETU_API_KEY` | — | Client API key (required) |
| `PYSETU_HOSTNAME` | `socket.gethostname()` | Endpoint identity |
| `PYSETU_BACKEND_URL` | `http://localhost:8001` | Control plane base URL |
| `PYSETU_POLL_INTERVAL` | `60` | Heartbeat/discovery interval (seconds) |
| `PYSETU_TELEMETRY_FILE` | `pysetu-agent-telemetry.jsonl` | Local offline event buffer |

A JSON config file is also supported via `PYSETU_CONFIG_FILE` or `--config`.

## Run

```bash
# single pass (registration + discovery + telemetry)
python -m pysetu_agent --once

# long-running daemon
python -m pysetu_agent

# scan a directory for secrets/PII and ingest findings
python -m pysetu_agent --scan-dir /path/to/project --policy-file policy.json

# watch a directory continuously and ingest findings as they appear
python -m pysetu_agent --watch /path/to/project --policy-file policy.json
```

## Run as a background service

> **macOS note:** launchd cannot execute scripts stored on an external volume
> (`/Volumes/…`). Copy the package onto the boot volume first:

```bash
cp -R pysetu_agent ~/pysetu-agent/
cp run-agent.sh ~/pysetu-agent/
cp deploy/agent-config.json ~/pysetu-agent/
```

Fill in `api_key` and `hostname` in `agent-config.json`, then install the service
(the plist references `~/pysetu-agent`):

```bash
# Linux (systemd)
sudo cp deploy/pysetu-agent.service /etc/systemd/system/pysetu-agent.service
sudo systemctl daemon-reload
sudo systemctl enable --now pysetu-agent

# macOS (launchd)
cp deploy/com.pysetu.agent.plist ~/Library/LaunchAgents/com.pysetu.agent.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.pysetu.agent.plist
```

The `run-agent.sh` wrapper sets `PYTHONPATH` and selects a Python 3.11+
interpreter, so the module resolves regardless of cwd or the Python on PATH.

To run watch mode as the service, change the `ExecStart` / `ProgramArguments`
to include `--watch /path/to/project`.

## Local DLP & policy

- `detection.py` — secrets (private keys, AWS/OpenAI/GitHub/Slack tokens, JWT,
  `key=value` assignments) and PII (SSN, email, phone, EU IDs, card numbers).
- `policy.py` — rule evaluation with `block > approval > redact > log > allow`
  precedence, plus an integrity-checked policy cache for offline decisions.
- `scan.py` — directory scanner that skips `.git`, `node_modules`, and build dirs.
- `shell.py` — shell command classifier (allow / approval / block).
- `watcher.py` — portable polling file watcher (snapshot diff → scan changed files).

When `--policy-file` is provided, `--scan-dir` fetches the effective policy from
the control plane (`GET /agentic/policy`) and caches it locally.

## Tests

```bash
python -m unittest discover -s tests
```

## Security notes

- Use a client API key scoped to a policy bundle, with no browser-only origin
  restriction, since the daemon calls the control plane server-to-server.
- No raw file contents are uploaded; the agent sends tool names, paths,
  classifications, decisions, and metadata only.
