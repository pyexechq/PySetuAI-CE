"""PySetu Endpoint Agent — discovery, telemetry, and enforcement daemon.

Discovery + telemetry (endpoint registration, heartbeat, AI tool discovery,
MCP discovery) plus local enforcement: file redaction/quarantine, shell-command
interception via PATH shims, clipboard DLP monitoring, and an MCP gateway that
intercepts tool-call traffic for AI desktop clients.
"""

__version__ = "0.5.0"
