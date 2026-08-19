# PySetu Endpoint Agent

Discovery + telemetry + enforcement daemon for the PySetu AI Control Plane.
Registers the endpoint, heartbeats, discovers installed AI tools and MCP
servers, ingests discovery events, and enforces local DLP: file
redaction/quarantine, shell-command interception via PATH shims, and clipboard
monitoring.

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

# scan AND enforce: redact PII files in place, quarantine blocked files
python -m pysetu_agent --scan-dir /path/to/project --policy-file policy.json --enforce

# watch a directory continuously and ingest findings as they appear
python -m pysetu_agent --watch /path/to/project --policy-file policy.json

# watch AND enforce (redact/quarantine on change)
python -m pysetu_agent --watch /path/to/project --policy-file policy.json --enforce

# install PATH shims to intercept claude/cursor/code invocations
python -m pysetu_agent --wrap-shell

# run the clipboard DLP monitor (macOS)
python -m pysetu_agent --clipboard
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
- `enforce.py` — real enforcement: redacts PII files in place (with a
  `*.pysetu.bak` backup) and quarantines blocked files to `~/.pysetu/quarantine`.
- `wrapper.py` — PATH shim that intercepts `claude`/`cursor`/`code` invocations,
  scanning argv and piped stdin for secrets/PII before the real binary runs.
- `clipboard.py` — macOS clipboard DLP monitor (`pbpaste`/`pbcopy`) that redacts
  or clears sensitive content copied to the clipboard.
- `mcp_gateway.py` — local MCP gateway that intercepts tool-call traffic for AI
  desktop clients (Claude Code, Claude Desktop, Cursor, VSCode), scanning
  `tools/call` arguments and blocking/redacting/passing through.

When `--policy-file` is provided, `--scan-dir` fetches the effective policy from
the control plane (`GET /agentic/policy`) and caches it locally.

## Enforcement

### File redaction & quarantine (`--enforce`)

During `--scan-dir` or `--watch`, `--enforce` turns policy decisions into real
on-disk actions:

- **redact** — the file is rewritten with the redacted content; the original is
  preserved as `*.pysetu.bak`.
- **block** — the file is moved to the quarantine directory
  (`--quarantine-dir`, default `~/.pysetu/quarantine`).

Writes are atomic (temp file + `os.replace`), so a crash never leaves a partial
file.

### Shell-command interception (`--wrap-shell`)

Installs executable shims for `claude`, `cursor`, and `code` into a directory
(default `~/.pysetu/bin`). Add that directory to the front of your `PATH`:

```bash
python -m pysetu_agent --wrap-shell
export PATH="$HOME/.pysetu/bin:$PATH"
```

Every invocation of a wrapped binary is scanned before the real binary runs:

- **argv** containing secrets/PII is **blocked** (argv cannot be safely
  rewritten).
- **piped stdin** containing PII is **redacted** before being passed to the real
  binary; stdin containing a blocked secret is **blocked**.

Recursion is prevented two ways: the shim directory is excluded when resolving
the real binary, and a `PYSETU_WRAPPER_ACTIVE` marker env var forces a
pass-through if the wrapper is ever re-entered.

### Clipboard monitor (`--clipboard`, macOS)

Polls the system clipboard and, when sensitive content is detected, redacts it
in place (or clears it for a block decision). Uses `pbpaste`/`pbcopy`.

### MCP gateway (`--mcp-gateway`)

Claude Code, Claude Desktop, Cursor, and VSCode all connect to MCP servers over
stdio. The gateway sits between the tool and a real MCP server: the tool is
pointed at the gateway as if it were an MCP server, and the gateway spawns the
real server as a subprocess and forwards JSON-RPC messages. Every `tools/call`
is scanned for secrets/PII and either **blocked**, **redacted**, or **passed
through** before reaching the real server.

Generate a config the tool can point at (writes `.mcp.json` or prints with `-`):

```bash
python -m pysetu_agent --mcp-gateway-config .mcp.json
python -m pysetu_agent --mcp-gateway-config -
```

Run the gateway proxying one discovered server:

```bash
python -m pysetu_agent --mcp-gateway --server github --policy-file policy.json
```

Behavior on `tools/call`:

- **block** — a JSON-RPC error is returned to the tool and the real server is
  never called (secrets, or a redaction that would produce invalid JSON).
- **redact** — the tool arguments are rewritten with `[REDACTED]` before being
  forwarded to the real server.
- **allow** — the call is forwarded unchanged.

Only stdio upstreams are proxied; HTTP/SSE servers are skipped by the config
generator. The proxy is a synchronous request/response forwarder.

## Tests

```bash
python -m unittest discover -s tests
```

## Security notes

- Use a client API key scoped to a policy bundle, with no browser-only origin
  restriction, since the daemon calls the control plane server-to-server.
- No raw file contents are uploaded; the agent sends tool names, paths,
  classifications, decisions, and metadata only.
- Redaction writes a `*.pysetu.bak` backup before rewriting; blocked files are
  moved to `~/.pysetu/quarantine` (never deleted).
- Sensitive data in argv is **blocked**, not rewritten — argv cannot be safely
  mutated without breaking the command.
- The clipboard monitor is macOS-only and depends on `pbpaste`/`pbcopy`.
