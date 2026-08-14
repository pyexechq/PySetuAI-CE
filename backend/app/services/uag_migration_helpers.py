"""Helpers for migrating legacy UAG configuration into routing rules and model registry."""

from __future__ import annotations

import json

PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o",
    "gemini": "gemini-1.5-pro",
    "claude": "claude-sonnet-4",
    "anthropic": "claude-sonnet-4",
    "ollama": "llama3.2",
    "azure_openai": "gpt-4o",
    "vllm": "meta-llama/Llama-3.1-8B-Instruct",
    "custom": "gpt-4o",
}


def uag_conditions_to_routing_condition(conditions: dict | None) -> str:
    if not conditions:
        return "default"
    clauses: list[str] = []
    for key, expected in conditions.items():
        if isinstance(expected, str):
            escaped = expected.replace("\\", "\\\\").replace('"', '\\"')
            clauses.append(f'{key} == "{escaped}"')
        elif isinstance(expected, bool):
            clauses.append(f"{key} == {str(expected)}")
        elif expected is None:
            clauses.append(f"{key} == None")
        else:
            clauses.append(f"{key} == {json.dumps(expected)}")
    return " and ".join(clauses)


def uag_policy_to_routing_fields(actions: dict | None) -> tuple[str, str | None, str]:
    actions = actions or {}
    route_to = actions.get("route_to") or actions.get("target_provider")
    emulate = actions.get("emulate") or actions.get("emulate_protocol") or "auto"
    if isinstance(emulate, str):
        response_format = emulate.strip().lower() or "auto"
    else:
        response_format = "auto"

    if route_to:
        provider = str(route_to).strip().lower()
        model = PROVIDER_DEFAULT_MODELS.get(provider, provider)
        return model, provider, response_format

    return "gpt-4o", None, response_format


def normalize_alias(value: str) -> str:
    return value.strip().lower()


def merge_aliases(existing: list | None, *aliases: str) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for raw in list(existing or []) + list(aliases):
        alias = raw.strip()
        if not alias:
            continue
        key = normalize_alias(alias)
        if key in seen:
            continue
        seen.add(key)
        merged.append(alias)
    return merged
