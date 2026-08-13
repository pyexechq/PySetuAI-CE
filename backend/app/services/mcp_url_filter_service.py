"""MCP web search + enterprise URL filtering (BL-071 / S12-07)."""

from __future__ import annotations

import fnmatch
import ipaddress
from typing import Any
from urllib.parse import urlparse

import httpx

WEB_SEARCH_TOOLS = {
    "brave_web_search",
    "brave_local_search",
    "web_search",
    "search",
    "google_search",
}
FETCH_TOOLS = {"fetch", "http_fetch", "get_url", "browse"}
URL_ARGUMENT_KEYS = ("url", "uri", "href", "link", "website", "target_url")
SUPPORTED_VENDORS = {"none", "zscaler", "fortigate", "cisco", "custom"}

DEFAULT_MCP_URL_FILTERS: dict[str, Any] = {
    "enabled": True,
    "mode": "denylist",
    "patterns": ["*.onion", "localhost", "127.0.0.1"],
    "block_private_ips": True,
    "web_search_enabled": True,
    "vendor": "none",
    "vendor_endpoint": "",
}


def merge_url_filters(raw: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(DEFAULT_MCP_URL_FILTERS)
    if isinstance(raw, dict):
        merged.update({key: raw[key] for key in merged if key in raw})
    mode = str(merged.get("mode") or "denylist").strip().lower()
    merged["mode"] = "allowlist" if mode == "allowlist" else "denylist"
    vendor = str(merged.get("vendor") or "none").strip().lower()
    merged["vendor"] = vendor if vendor in SUPPORTED_VENDORS else "none"
    patterns = merged.get("patterns")
    merged["patterns"] = [str(item).strip() for item in patterns if str(item).strip()] if isinstance(patterns, list) else []
    merged["enabled"] = bool(merged.get("enabled"))
    merged["block_private_ips"] = bool(merged.get("block_private_ips", True))
    merged["web_search_enabled"] = bool(merged.get("web_search_enabled", True))
    merged["vendor_endpoint"] = str(merged.get("vendor_endpoint") or "").strip()
    return merged


def public_url_filters(policy: dict[str, Any], *, vendor_configured: bool = False) -> dict[str, Any]:
    body = merge_url_filters(policy)
    body["vendor_configured"] = vendor_configured
    return body


def is_web_or_fetch_tool(tool_name: str) -> bool:
    key = (tool_name or "").strip().lower()
    return key in WEB_SEARCH_TOOLS or key in FETCH_TOOLS


def extract_urls_from_arguments(arguments: dict[str, Any] | None) -> list[str]:
    if not isinstance(arguments, dict):
        return []
    urls: list[str] = []
    for key in URL_ARGUMENT_KEYS:
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            urls.append(value.strip())
    for value in arguments.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and (item.startswith("http://") or item.startswith("https://")):
                    urls.append(item.strip())
    return urls


def _host_from_url(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.hostname or "").strip().lower()


def _is_private_host(host: str) -> bool:
    if not host:
        return True
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
        return bool(ip.is_private or ip.is_loopback or ip.is_link_local)
    except ValueError:
        return False


def _pattern_matches(host: str, pattern: str) -> bool:
    needle = pattern.strip().lower()
    if not needle:
        return False
    if "://" in needle:
        needle = _host_from_url(needle)
    if needle.startswith("*."):
        return host == needle[2:] or host.endswith(needle[1:])
    if "*" in needle:
        return fnmatch.fnmatch(host, needle)
    return host == needle or host.endswith(f".{needle}")


def url_matches_policy(url: str, policy: dict[str, Any]) -> bool:
    """Return True when URL is allowed under tenant policy."""
    merged = merge_url_filters(policy)
    if not merged["enabled"]:
        return True

    host = _host_from_url(url)
    if not host:
        return merged["mode"] != "allowlist"

    if merged["block_private_ips"] and _is_private_host(host):
        return merged["mode"] == "allowlist"

    patterns = merged["patterns"]
    matched = any(_pattern_matches(host, pattern) for pattern in patterns)
    if merged["mode"] == "allowlist":
        return matched
    return not matched


async def query_vendor(url: str, policy: dict[str, Any], vendor_api_key: str | None) -> tuple[bool | None, str]:
    merged = merge_url_filters(policy)
    vendor = merged["vendor"]
    endpoint = merged["vendor_endpoint"]
    if vendor == "none" or not endpoint:
        return None, ""
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if vendor_api_key:
        headers["Authorization"] = f"Bearer {vendor_api_key}"
    payload = {"url": url, "vendor": vendor, "action": "classify"}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
        if isinstance(body, dict) and "allowed" in body:
            allowed = bool(body.get("allowed"))
            reason = str(body.get("reason") or f"Blocked by {vendor} integration")
            return allowed, reason
    except Exception as exc:
        return False, f"Vendor URL filter check failed: {exc}"
    return False, f"Vendor {vendor} returned an invalid response"


async def evaluate_tool_access(
    tool_name: str,
    arguments: dict[str, Any] | None,
    policy: dict[str, Any],
    *,
    vendor_api_key: str | None = None,
) -> tuple[bool, str]:
    name = (tool_name or "").strip().lower()
    merged = merge_url_filters(policy)
    if not merged["enabled"]:
        return True, ""

    if name in WEB_SEARCH_TOOLS:
        if merged["web_search_enabled"]:
            return True, ""
        return False, "Web search MCP tools are disabled by URL filter policy"

    if name not in FETCH_TOOLS and not extract_urls_from_arguments(arguments):
        return True, ""

    urls = extract_urls_from_arguments(arguments)
    if not urls and name in FETCH_TOOLS:
        return False, "Fetch tool requires a URL argument"

    for url in urls:
        if not url_matches_policy(url, merged):
            return False, f"URL blocked by tenant policy: {url}"
        vendor_result, vendor_reason = await query_vendor(url, merged, vendor_api_key)
        if vendor_result is False:
            return False, vendor_reason or f"URL blocked by vendor filter: {url}"
    return True, ""


def probe_url(url: str, policy: dict[str, Any]) -> dict[str, Any]:
    merged = merge_url_filters(policy)
    allowed = url_matches_policy(url, merged)
    host = _host_from_url(url)
    return {
        "url": url,
        "host": host,
        "allowed": allowed,
        "mode": merged["mode"],
        "private_host": _is_private_host(host),
    }
