"""MCP agent auto-detection and per-agent access toggles (BL-069 / S12-05)."""

from __future__ import annotations

from typing import Any

KNOWN_AGENTS = ("claude", "openai", "gemini", "cursor", "unknown")
DEFAULT_AGENT_TOGGLES: dict[str, bool] = {slug: True for slug in KNOWN_AGENTS}


def detect_agent(user_agent: str | None, metadata: dict | None) -> str:
    meta = metadata if isinstance(metadata, dict) else {}
    for key in ("agent", "client_agent", "mcp_agent"):
        raw = meta.get(key)
        if isinstance(raw, str) and raw.strip():
            slug = normalize_agent_slug(raw)
            if slug in KNOWN_AGENTS:
                return slug
    hint = meta.get("user_agent")
    if isinstance(hint, str) and hint.strip():
        return classify_user_agent(hint)
    return classify_user_agent(user_agent or "")


def normalize_agent_slug(value: str) -> str:
    slug = value.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "chatgpt": "openai",
        "gpt": "openai",
        "anthropic": "claude",
        "google": "gemini",
        "google_gemini": "gemini",
    }
    return aliases.get(slug, slug)


def classify_user_agent(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if not ua.strip():
        return "unknown"
    if "claude" in ua or "anthropic" in ua:
        return "claude"
    if "openai" in ua or "chatgpt" in ua or "gpt-" in ua:
        return "openai"
    if "gemini" in ua or "google-ai" in ua or "bard" in ua:
        return "gemini"
    if "cursor" in ua:
        return "cursor"
    if "pysetu" in ua:
        return "unknown"
    return "unknown"


def toggles_from_tenant(raw: dict | None) -> dict[str, bool]:
    merged = dict(DEFAULT_AGENT_TOGGLES)
    if not isinstance(raw, dict):
        return merged
    for slug in KNOWN_AGENTS:
        value = raw.get(slug)
        if isinstance(value, bool):
            merged[slug] = value
        elif isinstance(value, dict) and "enabled" in value:
            merged[slug] = bool(value["enabled"])
    return merged


def merge_agent_toggles(existing: dict[str, bool] | None, patch: dict[str, bool]) -> dict[str, bool]:
    merged = toggles_from_tenant(existing)
    for slug in KNOWN_AGENTS:
        if slug in patch:
            merged[slug] = bool(patch[slug])
    return merged


def is_mcp_enabled_for_agent(toggles: dict[str, bool], agent: str) -> bool:
    slug = normalize_agent_slug(agent)
    if slug not in KNOWN_AGENTS:
        slug = "unknown"
    return bool(toggles.get(slug, True))


def server_allows_agent(server: Any, agent: str) -> bool:
    config = getattr(server, "connection_config", None) or {}
    if not isinstance(config, dict):
        return True
    allowed = config.get("allowed_agents")
    if not isinstance(allowed, list) or not allowed:
        return True
    slug = normalize_agent_slug(agent)
    if slug not in KNOWN_AGENTS:
        slug = "unknown"
    normalized = {normalize_agent_slug(str(item)) for item in allowed}
    return slug in normalized


def filter_servers_for_agent(
    servers: list[Any],
    agent: str,
    toggles: dict[str, bool],
) -> list[Any]:
    if not is_mcp_enabled_for_agent(toggles, agent):
        return []
    return [server for server in servers if server_allows_agent(server, agent)]


def apply_allowed_agents_to_config(connection_config: dict | None, allowed_agents: list[str] | None) -> dict:
    config = dict(connection_config or {})
    if allowed_agents is None:
        return config
    cleaned = [normalize_agent_slug(str(item)) for item in allowed_agents if str(item).strip()]
    config["allowed_agents"] = [slug for slug in cleaned if slug in KNOWN_AGENTS]
    return config


def public_agent_settings(toggles: dict[str, bool]) -> list[dict[str, Any]]:
    labels = {
        "claude": "Claude / Anthropic",
        "openai": "OpenAI / ChatGPT",
        "gemini": "Google Gemini",
        "cursor": "Cursor",
        "unknown": "Other clients",
    }
    return [
        {"slug": slug, "label": labels[slug], "enabled": bool(toggles.get(slug, True))}
        for slug in KNOWN_AGENTS
    ]
