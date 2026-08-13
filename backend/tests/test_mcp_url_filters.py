"""Tests for MCP URL filter policy (BL-071 / S12-07)."""

import asyncio

from app.services.mcp_url_filter_service import (
    DEFAULT_MCP_URL_FILTERS,
    evaluate_tool_access,
    extract_urls_from_arguments,
    merge_url_filters,
    probe_url,
    url_matches_policy,
)


def test_merge_url_filters_defaults() -> None:
    merged = merge_url_filters(None)
    assert merged["enabled"] is True
    assert merged["mode"] == "denylist"
    assert merged["vendor"] == "none"


def test_extract_urls_from_arguments() -> None:
    urls = extract_urls_from_arguments({"url": "https://example.com/docs"})
    assert urls == ["https://example.com/docs"]


def test_denylist_blocks_pattern() -> None:
    policy = dict(DEFAULT_MCP_URL_FILTERS)
    policy["patterns"] = ["evil.com"]
    assert url_matches_policy("https://api.evil.com/path", policy) is False
    assert url_matches_policy("https://safe.com", policy) is True


def test_allowlist_requires_match() -> None:
    policy = dict(DEFAULT_MCP_URL_FILTERS)
    policy["mode"] = "allowlist"
    policy["patterns"] = ["trusted.com"]
    assert url_matches_policy("https://app.trusted.com", policy) is True
    assert url_matches_policy("https://other.com", policy) is False


def test_block_private_ips() -> None:
    policy = dict(DEFAULT_MCP_URL_FILTERS)
    policy["block_private_ips"] = True
    assert url_matches_policy("http://10.0.0.5", policy) is False


def test_web_search_disabled() -> None:
    policy = dict(DEFAULT_MCP_URL_FILTERS)
    policy["web_search_enabled"] = False
    allowed, reason = asyncio.run(evaluate_tool_access("brave_web_search", {"query": "news"}, policy))
    assert allowed is False
    assert "disabled" in reason.lower()


def test_fetch_requires_url() -> None:
    policy = dict(DEFAULT_MCP_URL_FILTERS)
    allowed, reason = asyncio.run(evaluate_tool_access("fetch", {}, policy))
    assert allowed is False
    assert "requires" in reason.lower()


def test_probe_url() -> None:
    result = probe_url("https://example.com", DEFAULT_MCP_URL_FILTERS)
    assert result["allowed"] is True
    assert result["host"] == "example.com"
