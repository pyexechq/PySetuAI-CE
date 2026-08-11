"""Build routing context for LLM rule evaluation from gateway requests."""

from __future__ import annotations

import json
import re
from typing import Any

from app.schemas.openai import ChatCompletionRequest, ChatMessage

_IMAGE_HINTS = ("data:image", "[image]", "image attached", "see attached image")
_CODE_REVIEW_HINTS = ("code review", "review this code", "pull request", "pr review", "review my code")


def _deep_get(target: dict[str, Any], path: list[str]) -> Any:
    current: Any = target
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _deep_set_if_missing(target: dict[str, Any], path: list[str], value: Any) -> None:
    current = target
    for part in path[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    if _deep_get(target, path) is None:
        current[path[-1]] = value


def _merge_context(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = {**base}
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_context(merged[key], value)
        elif key not in merged or merged[key] is None:
            merged[key] = value
    return merged


def _parse_system_context(content: str) -> dict[str, Any]:
    content = content.strip()
    if not content:
        return {}

    if content.startswith("{"):
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    ctx: dict[str, Any] = {}
    for match in re.finditer(r"([\w.]+)\s*==\s*['\"]([^'\"]+)['\"]", content):
        path = match.group(1).split(".")
        _deep_set_if_missing(ctx, path, match.group(2))
    return ctx


def infer_routing_context(messages: list[ChatMessage]) -> dict[str, Any]:
    ctx: dict[str, Any] = {}
    combined = " ".join(message.content for message in messages).lower()

    if any(hint in combined for hint in _CODE_REVIEW_HINTS):
        _deep_set_if_missing(ctx, ["task", "type"], "code_review")

    has_image = any(hint in combined for hint in _IMAGE_HINTS)
    _deep_set_if_missing(ctx, ["input", "has_image"], has_image)

    for message in messages:
        if message.role == "system":
            ctx = _merge_context(ctx, _parse_system_context(message.content))

    return ctx


def build_routing_context(request: ChatCompletionRequest) -> dict[str, Any]:
    explicit = request.routing_context or {}
    inferred = infer_routing_context(request.messages)
    return _merge_context(explicit, inferred)
