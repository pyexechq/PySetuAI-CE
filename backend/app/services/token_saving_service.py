"""Token saving engine — JSON→TOON compression and markdown stripping (BL-063)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.schemas.openai import ChatMessage

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*\n([\s\S]*?)\n```", re.IGNORECASE)
_MARKDOWN_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^#{1,6}\s+", re.MULTILINE), ""),
    (re.compile(r"\*\*([^*]+)\*\*"), r"\1"),
    (re.compile(r"__([^_]+)__"), r"\1"),
    (re.compile(r"\*([^*]+)\*"), r"\1"),
    (re.compile(r"_([^_]+)_"), r"\1"),
    (re.compile(r"~~([^~]+)~~"), r"\1"),
    (re.compile(r"!\[([^\]]*)\]\([^)]+\)"), r"\1"),
    (re.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"),
    (re.compile(r"^>\s?", re.MULTILINE), ""),
    (re.compile(r"^[-*+]\s+", re.MULTILINE), ""),
    (re.compile(r"^\d+\.\s+", re.MULTILINE), ""),
    (re.compile(r"`([^`]+)`"), r"\1"),
    (re.compile(r"```[\s\S]*?```"), ""),
    (re.compile(r"\n{3,}"), "\n\n"),
]


@dataclass
class TokenSavingResult:
    messages: list[ChatMessage]
    enabled: bool
    mode: str
    original_tokens: int
    compressed_tokens: int
    tokens_saved: int
    savings_pct: float
    transformations: int


def estimate_tokens(text: str) -> int:
    """Approximate token count (~4 chars per token)."""
    return max(1, len(text) // 4) if text.strip() else 0


def strip_markdown(text: str) -> str:
    result = text
    for pattern, replacement in _MARKDOWN_PATTERNS:
        result = pattern.sub(replacement, result)
    return result.strip()


def _is_primitive(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _format_primitive(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        if re.search(r'[,\n:"\\]', value) or value.strip() != value:
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return value
    return str(value)


def _is_uniform_object_array(items: list[Any]) -> tuple[bool, list[str]]:
    if not items or not all(isinstance(item, dict) for item in items):
        return False, []
    field_sets = [tuple(item.keys()) for item in items]
    if len({fs for fs in field_sets}) != 1:
        return False, []
    fields = list(items[0].keys())
    for item in items:
        if not all(_is_primitive(item.get(f)) for f in fields):
            return False, []
    return True, fields


def _encode_value(value: Any, indent: int = 0) -> str:
    pad = "  " * indent
    if _is_primitive(value):
        return _format_primitive(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        is_uniform, fields = _is_uniform_object_array(value)
        if is_uniform and fields:
            lines = [f"{pad}[{len(value)}]{{{','.join(fields)}}}:"]
            for item in value:
                row = ",".join(_format_primitive(item.get(f)) for f in fields)
                lines.append(f"{pad}  {row}")
            return "\n".join(lines)
        lines = [f"{pad}[{len(value)}]:"]
        for item in value:
            encoded = _encode_value(item, indent + 1)
            if "\n" in encoded:
                lines.append(f"{pad}  -")
                lines.extend(f"{pad}    {line}" for line in encoded.splitlines())
            else:
                lines.append(f"{pad}  - {encoded}")
        return "\n".join(lines)
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines: list[str] = []
        for key, val in value.items():
            encoded = _encode_value(val, indent + 1)
            if "\n" in encoded:
                lines.append(f"{pad}{key}:")
                lines.extend(f"{pad}  {line}" for line in encoded.splitlines())
            else:
                lines.append(f"{pad}{key}: {encoded}")
        return "\n".join(lines)
    return json.dumps(value, separators=(",", ":"))


def json_to_toon(data: Any) -> str:
    """Encode JSON-serializable data as TOON (Token-Oriented Object Notation)."""
    return _encode_value(data)


def _try_parse_json(text: str) -> Any | None:
    stripped = text.strip()
    if not stripped:
        return None
    if stripped[0] not in "{[":
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _compress_json_block(raw_json: str) -> tuple[str, bool]:
    parsed = _try_parse_json(raw_json)
    if parsed is None:
        return raw_json, False
    toon = json_to_toon(parsed)
    original_len = len(raw_json.strip())
    if len(toon) < original_len * 0.85:
        return toon, True
    return raw_json, False


def compress_message_content(content: str, mode: str) -> tuple[str, int]:
    """Apply token-saving transforms to a single message. Returns (content, transform_count)."""
    transforms = 0
    result = content

    if mode in ("strip_markdown", "both"):
        stripped = strip_markdown(result)
        if stripped != result:
            result = stripped
            transforms += 1

    if mode in ("json_to_toon", "both"):
        def _replace_fence(match: re.Match[str]) -> str:
            nonlocal transforms
            inner = match.group(1)
            compressed, changed = _compress_json_block(inner)
            if changed:
                transforms += 1
                return f"```toon\n{compressed}\n```"
            return match.group(0)

        result = _JSON_FENCE_RE.sub(_replace_fence, result)

        parsed = _try_parse_json(result)
        if parsed is not None:
            compressed, changed = _compress_json_block(result)
            if changed:
                result = compressed
                transforms += 1

    return result, transforms


def resolve_token_saving_config(
    *,
    tenant_enabled: bool,
    tenant_mode: str,
    request_metadata: dict | None,
    key_enabled: bool | None = None,
    key_mode: str | None = None,
) -> tuple[bool, str]:
    """Resolve token saving from per-key settings, tenant default, and request metadata."""
    enabled = key_enabled if key_enabled is not None else tenant_enabled
    mode = key_mode if key_mode is not None else (tenant_mode or "both")

    if request_metadata:
        if "token_saving" in request_metadata:
            enabled = bool(request_metadata["token_saving"])
        if request_metadata.get("token_saving_mode"):
            mode = str(request_metadata["token_saving_mode"])

    if mode not in ("json_to_toon", "strip_markdown", "both"):
        mode = "both"
    return enabled, mode


def apply_token_saving(
    messages: list[ChatMessage],
    *,
    enabled: bool,
    mode: str = "both",
) -> TokenSavingResult:
    """Compress ingress message content. Responses are never modified."""
    original_text = "\n".join(m.content for m in messages)
    original_tokens = estimate_tokens(original_text)

    if not enabled:
        return TokenSavingResult(
            messages=messages,
            enabled=False,
            mode=mode,
            original_tokens=original_tokens,
            compressed_tokens=original_tokens,
            tokens_saved=0,
            savings_pct=0.0,
            transformations=0,
        )

    new_messages: list[ChatMessage] = []
    total_transforms = 0
    for msg in messages:
        if msg.role in ("user", "tool") and msg.content:
            compressed, count = compress_message_content(msg.content, mode)
            new_messages.append(ChatMessage(role=msg.role, content=compressed))
            total_transforms += count
        else:
            new_messages.append(msg)

    compressed_text = "\n".join(m.content for m in new_messages)
    compressed_tokens = estimate_tokens(compressed_text)
    tokens_saved = max(0, original_tokens - compressed_tokens)
    savings_pct = round((tokens_saved / original_tokens) * 100, 1) if original_tokens else 0.0

    return TokenSavingResult(
        messages=new_messages,
        enabled=True,
        mode=mode,
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        tokens_saved=tokens_saved,
        savings_pct=savings_pct,
        transformations=total_transforms,
    )


def summarize_token_saving(usage_rows: list[dict | None]) -> dict:
    """Aggregate before/after token saving from audit usage_metadata rows."""
    original = 0
    compressed = 0
    requests_compressed = 0
    for row in usage_rows:
        if not row:
            continue
        payload = row.get("token_saving") if isinstance(row, dict) else None
        if not isinstance(payload, dict) or not payload.get("enabled"):
            continue
        before = int(payload.get("original_tokens") or 0)
        after = int(payload.get("compressed_tokens") or 0)
        saved = max(0, before - after)
        if saved <= 0:
            continue
        original += before
        compressed += after
        requests_compressed += 1
    tokens_saved = max(0, original - compressed)
    savings_pct = round((tokens_saved / original) * 100, 1) if original else 0.0
    return {
        "requests_compressed": requests_compressed,
        "original_tokens": original,
        "compressed_tokens": compressed,
        "tokens_saved": tokens_saved,
        "savings_pct": savings_pct,
    }
