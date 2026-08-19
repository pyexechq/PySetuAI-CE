# Agent Control Plane Roadmap

> Phased rollout of the Unified AI Agent Control Plane. Phases 1-5 are complete and committed.

## Phase 1 — Foundation (done)

- Endpoint registration + heartbeat
- Endpoint inventory
- Agent inventory + capability model
- Unified security-event ingestion linked to Audit Explorer
- Deterministic risk scoring
- Agent Inventory and Endpoint Security dashboards

## Phase 2 — Endpoint Enforcement (done)

- Signed, least-privilege endpoint daemon (Windows / macOS / Linux)
- AI tool discovery (process, config, IDE extension, MCP config) — done
- Local DLP + secret detection — done
- File and shell governance via supported OS APIs and adapters — file scan + polling watcher done, native FSEvents/inotify pending
- Offline policy cache with queued telemetry — done
- Policy sync endpoint — done
- Shell command governance (heuristic pre-filter) — done
- Approval workflow — backend model + API done, UI done
- `--watch` continuous mode + launchd/systemd service packaging — done

## Phase 3 — MCP Governance Depth (done)

- Per-tool MCP governance policies (allow / approval / block) — done
- Tool-chain risk scoring (deterministic 0-100) — done
- MCP tool-chain event monitoring + summary — done
- Agentic attack-surface graph (agent → agent → server → tool → data → external) — done
- Approval center integration for MCP tool calls (gateway before_invoke) — done
- MCP Tool Chains UI (`/mcp-tool-chains`) — done
- MCP discovery from endpoint configs — done (`.mcp.json`, `.cursor/mcp.json`, Claude Desktop config)
- Agent-to-agent event monitoring (source/target agent attribution) — done (source agent resolved from gateway actor)

## Phase 4 — Microsoft Copilot (done)

- Microsoft Copilot / Teams / Copilot Studio inventory — done
- Connector inventory and risk assessment — done
- Graph / audit / security API synchronization — done (payload-driven sync adapter; MS Graph OAuth is tenant-side)
- Governance drift detection — done (baseline capture + drift comparison)

## Phase 5 — Advanced Agentic Security (done)

- Agent chains and attack-surface visualization — done (Phase 3 graph)
- Anomaly and behavior detection — done (volume, tool usage, data access, timing, chain risk)
- Prompt-injection detection in files/repos/MCP resources — done (wraps existing `scan_content`)
- Exfiltration detection — done (large read, rapid read, sensitive boundary exit)
- Guardian policy enforcement loop — done (severity→action evaluation + on-demand run + Celery beat schedule `run_guardian_loop_all_tenants`)
- Automated remediation — done (block agent, revoke access, quarantine, alert)

## Compliance mapping

Events and controls map to NIST AI RMF, NIST CSF, ISO 27001, SOC 2, GDPR, HIPAA, and PCI DSS
through the existing Compliance Center.
