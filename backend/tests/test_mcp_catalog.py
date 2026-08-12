"""Tests for curated MCP catalog + one-click install (BL-066 / S12-02)."""

from app.services.mcp_catalog_service import (
    catalog_slug_installed,
    custom_install_spec,
    get_catalog_entry,
    install_spec_from_entry,
    list_catalog_entries,
)


def test_catalog_has_curated_entries() -> None:
    entries = list_catalog_entries()
    slugs = {e["slug"] for e in entries}
    assert "github" in slugs
    assert "filesystem" in slugs
    assert "postgres" in slugs
    assert len(entries) >= 6
    github = get_catalog_entry("github")
    assert github is not None
    assert github["transport"] in {"sse", "stdio", "streamable_http"}
    assert github["name"]
    assert github["category"]


def test_get_catalog_entry_unknown() -> None:
    assert get_catalog_entry("not-a-real-mcp") is None


def test_install_spec_from_entry_sets_catalog_slug() -> None:
    entry = get_catalog_entry("github")
    assert entry is not None
    spec = install_spec_from_entry(entry, endpoint_url="https://mcp.example.com/github")
    assert spec["name"] == entry["name"]
    assert spec["category"] == entry["category"]
    assert spec["transport"] == entry["transport"]
    assert spec["endpoint_url"] == "https://mcp.example.com/github"
    assert spec["connection_config"]["catalog_slug"] == "github"
    assert spec["status"] == "offline"


def test_install_spec_uses_default_endpoint_when_not_overridden() -> None:
    entry = get_catalog_entry("fetch")
    assert entry is not None
    spec = install_spec_from_entry(entry)
    assert spec["endpoint_url"] == entry.get("default_endpoint")


def test_catalog_slug_installed_detects_existing() -> None:
    servers = [
        type("S", (), {"connection_config": {"catalog_slug": "github"}, "name": "GitHub"})(),
        type("S", (), {"connection_config": {}, "name": "Other"})(),
    ]
    assert catalog_slug_installed(servers, "github") is True
    assert catalog_slug_installed(servers, "postgres") is False


def test_custom_install_spec_from_transport_url() -> None:
    spec = custom_install_spec(
        name="Internal Wiki",
        endpoint_url="https://wiki.corp.example/mcp",
        transport="sse",
        category="Knowledge",
    )
    assert spec["name"] == "Internal Wiki"
    assert spec["endpoint_url"] == "https://wiki.corp.example/mcp"
    assert spec["transport"] == "sse"
    assert spec["connection_config"]["catalog_slug"] == "custom"
    assert spec["status"] == "offline"


def test_custom_install_rejects_empty_url() -> None:
    try:
        custom_install_spec(name="X", endpoint_url="  ", transport="sse")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "url" in str(exc).lower()
