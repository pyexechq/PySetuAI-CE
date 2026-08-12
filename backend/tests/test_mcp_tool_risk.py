"""Tests for MCP tool risk taxonomy and auto-hide (BL-068 / S12-04)."""

from app.services.mcp_tool_risk_service import (
    annotate_tools,
    classify_tool_risk,
    is_tool_hidden,
    merge_tool_policies,
    visible_tools,
)


def test_classify_read_write_destructive() -> None:
    assert classify_tool_risk("search_code") == "read"
    assert classify_tool_risk("get_file") == "read"
    assert classify_tool_risk("list_issues") == "read"
    assert classify_tool_risk("create_issue") == "write"
    assert classify_tool_risk("update_page") == "write"
    assert classify_tool_risk("delete_file") == "destructive"
    assert classify_tool_risk("drop_table") == "destructive"
    assert classify_tool_risk("purge_cache") == "destructive"


def test_classify_uses_description_when_name_is_neutral() -> None:
    assert classify_tool_risk("run_action", "Permanently delete a repository") == "destructive"
    assert classify_tool_risk("run_action", "Create a new draft") == "write"
    assert classify_tool_risk("run_action", "Fetch metadata") == "read"


def test_is_tool_hidden_explicit_and_auto_destructive() -> None:
    assert is_tool_hidden({"risk": "read", "hidden": True}, auto_hide_destructive=False) is True
    assert is_tool_hidden({"risk": "destructive", "hidden": False}, auto_hide_destructive=False) is False
    assert is_tool_hidden({"risk": "destructive", "hidden": False}, auto_hide_destructive=True) is True
    assert is_tool_hidden({"risk": "write", "hidden": False}, auto_hide_destructive=True) is False


def test_visible_tools_drops_hidden_and_auto_hidden() -> None:
    tools = [
        {"name": "search", "description": "Find files"},
        {"name": "delete_file", "description": "Remove a file"},
        {"name": "draft", "description": "Unused"},
    ]
    policies = {"draft": {"hidden": True}}
    visible = visible_tools(tools, policies, auto_hide_destructive=True)
    names = [t["name"] for t in visible]
    assert names == ["search"]


def test_annotate_tools_includes_risk_and_hidden_flags() -> None:
    tools = [{"name": "delete_file", "description": ""}, {"name": "search", "description": "Find"}]
    annotated = annotate_tools(tools, {"search": {"hidden": True}}, auto_hide_destructive=True)
    delete = next(t for t in annotated if t["name"] == "delete_file")
    search = next(t for t in annotated if t["name"] == "search")
    assert delete["risk"] == "destructive"
    assert delete["hidden"] is False
    assert delete["auto_hidden"] is True
    assert delete["visible"] is False
    assert search["risk"] == "read"
    assert search["hidden"] is True
    assert search["visible"] is False


def test_merge_tool_policies_keeps_overrides() -> None:
    merged = merge_tool_policies(
        {"search": {"risk": "read", "hidden": False}},
        [{"name": "search", "hidden": True}, {"name": "delete_file", "risk": "write"}],
    )
    assert merged["search"]["hidden"] is True
    assert merged["search"]["risk"] == "read"
    assert merged["delete_file"]["risk"] == "write"
    assert merged["delete_file"]["hidden"] is False
