# Agent Control Plane Roadmap

> Phased rollout of the Unified AI Agent Control Plane. Phase 1 foundation is in progress.

## Phase 1 — Foundation (current)

- Endpoint registration + heartbeat
- Endpoint inventory
- Agent inventory + capability model
- Unified security-event ingestion linked to Audit Explorer
- Deterministic risk scoring
- Agent Inventory and Endpoint Security dashboards

## Phase 2 — Endpoint Enforcement (in progress)

- Signed, least-privilege endpoint daemon (Windows / macOS / Linux)
- AI tool discovery (process, config, IDE extension, MCP config) — done
- Local DLP + secret detection — done
- File and shell governance via supported OS APIs and adapters — file scan + polling watcher done, native FSEvents/inotify pending
- Offline policy cache with queued telemetry — done
- Policy sync endpoint — done
- Shell command governance (heuristic pre-filter) — done
- Approval workflow — backend model + API done, UI done
- `--watch` continuous mode + launchd/systemd service packaging — done

## Phase 3 — MCP Governance Depth

- MCP discovery from endpoint configs
- Tool-chain governance and risk scoring
- Agent-to-agent / MCP event monitoring
- Approval center integration

## Phase 4 — Microsoft Copilot

- Microsoft Copilot / Teams / Copilot Studio inventory
- Connector inventory and risk assessment
- Graph / audit / security API synchronization
- Governance drift detection

## Phase 5 — Advanced Agentic Security

- Agent chains and attack-surface visualization
- Anomaly and behavior detection
- Prompt-injection detection in files/repos/MCP resources
- Exfiltration detection
- Guardian policy enforcement loop
- Automated remediation

## Compliance mapping

Events and controls map to NIST AI RMF, NIST CSF, ISO 27001, SOC 2, GDPR, HIPAA, and PCI DSS
through the existing Compliance Center.
