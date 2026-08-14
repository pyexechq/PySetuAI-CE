"""Tests for token saving engine (BL-063 / S11-01)."""

import json

from app.schemas.openai import ChatMessage
from app.services.token_saving_service import (
    apply_token_saving,
    compress_message_content,
    estimate_tokens,
    json_to_toon,
    resolve_token_saving_config,
    strip_markdown,
)


def test_strip_markdown_removes_formatting():
    raw = "# Title\n\n**Bold** and *italic* with [link](https://example.com)\n\n- item one\n- item two"
    result = strip_markdown(raw)
    assert "#" not in result
    assert "**" not in result
    assert "Bold" in result
    assert "link" in result


def test_json_to_toon_uniform_array():
    data = [
        {"id": 1, "name": "Alice", "role": "admin"},
        {"id": 2, "name": "Bob", "role": "user"},
    ]
    toon = json_to_toon(data)
    assert "[2]{id,name,role}:" in toon
    assert "1,Alice,admin" in toon
    assert "2,Bob,user" in toon


def test_json_to_toon_saves_tokens_on_uniform_data():
    data = [{"id": i, "name": f"User{i}", "role": "member"} for i in range(20)]
    compact_json = json.dumps(data, separators=(",", ":"))
    toon = json_to_toon(data)
    assert estimate_tokens(toon) < estimate_tokens(compact_json)


def test_compress_message_content_json_fence():
    payload = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    content = f"Analyze this data:\n```json\n{json.dumps(payload, indent=2)}\n```"
    compressed, transforms = compress_message_content(content, "json_to_toon")
    assert transforms == 1
    assert "```toon" in compressed
    assert "Alice" in compressed


def test_apply_token_saving_disabled():
    messages = [ChatMessage(role="user", content="Hello world")]
    result = apply_token_saving(messages, enabled=False)
    assert result.enabled is False
    assert result.tokens_saved == 0
    assert result.messages[0].content == "Hello world"


def test_apply_token_saving_compresses_user_messages_only():
    json_block = json.dumps([{"id": 1, "value": "test"}, {"id": 2, "value": "demo"}], indent=2)
    messages = [
        ChatMessage(role="system", content=f"```json\n{json_block}\n```"),
        ChatMessage(role="user", content=f"```json\n{json_block}\n```"),
    ]
    result = apply_token_saving(messages, enabled=True, mode="json_to_toon")
    assert result.enabled is True
    assert result.transformations >= 1
    assert "```toon" in result.messages[1].content
    assert "```json" in result.messages[0].content


def test_resolve_token_saving_config_request_override():
    enabled, mode = resolve_token_saving_config(
        tenant_enabled=False,
        tenant_mode="both",
        request_metadata={"token_saving": True, "token_saving_mode": "strip_markdown"},
    )
    assert enabled is True
    assert mode == "strip_markdown"


def test_resolve_token_saving_config_key_override():
    enabled, mode = resolve_token_saving_config(
        tenant_enabled=False,
        tenant_mode="both",
        request_metadata=None,
        key_enabled=True,
        key_mode="json_to_toon",
    )
    assert enabled is True
    assert mode == "json_to_toon"


def test_resolve_token_saving_config_key_inherits_tenant():
    enabled, mode = resolve_token_saving_config(
        tenant_enabled=True,
        tenant_mode="strip_markdown",
        request_metadata=None,
        key_enabled=None,
        key_mode=None,
    )
    assert enabled is True
    assert mode == "strip_markdown"


def test_resolve_token_saving_config_invalid_mode_falls_back():
    enabled, mode = resolve_token_saving_config(
        tenant_enabled=True,
        tenant_mode="invalid",
        request_metadata=None,
    )
    assert enabled is True
    assert mode == "both"
