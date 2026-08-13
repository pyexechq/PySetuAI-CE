"""Tests for REST-to-MCP spec proxy parsing (BL-083 / Sprint 15)."""

import pytest

from app.services.mcp_spec_proxy_service import (
    parse_graphql_sdl,
    parse_openapi_spec,
    parse_postman_spec,
    parse_spec,
    to_tool_name,
)


def test_to_tool_name_normalizes() -> None:
    assert to_tool_name("List Users") == "list_users"
    assert to_tool_name("get /users/{id}") == "get_users_id"
    assert to_tool_name("  ") == "unnamed_tool"


def test_parse_openapi_spec_extracts_tools_and_base_url() -> None:
    spec = {
        "servers": [{"url": "https://api.example.com"}],
        "paths": {
            "/users": {
                "get": {
                    "operationId": "listUsers",
                    "summary": "List all users",
                    "tags": ["users"],
                },
                "post": {"summary": "Create a user"},
            }
        },
    }
    tools, endpoint = parse_openapi_spec(spec)
    assert endpoint == "https://api.example.com"
    names = {t["name"] for t in tools}
    assert "listusers" in names
    assert "post_users" in names
    get_tool = next(t for t in tools if t["name"] == "listusers")
    assert get_tool["method"] == "GET"
    assert get_tool["path"] == "/users"
    assert get_tool["tags"] == ["users"]


def test_parse_openapi_swagger2_host() -> None:
    spec = {
        "host": "api.legacy.io",
        "schemes": ["https"],
        "basePath": "/v1",
        "paths": {"/ping": {"get": {"operationId": "ping"}}},
    }
    tools, endpoint = parse_openapi_spec(spec)
    assert endpoint == "https://api.legacy.io/v1"
    assert tools[0]["name"] == "ping"


def test_parse_postman_collection_recurses_folders() -> None:
    collection = {
        "info": {"name": "Internal API"},
        "item": [
            {"name": "Folder", "item": [{"name": "List Orders", "request": {"method": "GET", "url": {"path": ["orders"]}}}]},
            {"name": "Create Order", "request": {"method": "POST", "url": "https://api.example.com/orders"}},
        ],
    }
    tools, server_name = parse_postman_spec(collection)
    assert server_name == "Internal API"
    names = {t["name"] for t in tools}
    assert names == {"list_orders", "create_order"}
    create = next(t for t in tools if t["name"] == "create_order")
    assert create["method"] == "POST"


def test_parse_graphql_sdl_extracts_query_and_mutation() -> None:
    sdl = """
    type Query {
      users(limit: Int): [User]
    }
    type Mutation {
      createUser(name: String): User
    }
    """
    tools, endpoint = parse_graphql_sdl(sdl)
    assert endpoint == ""
    by_name = {t["name"]: t for t in tools}
    assert by_name["users"]["method"] == "QUERY"
    assert by_name["createuser"]["method"] == "MUTATION"


@pytest.mark.anyio
async def test_parse_spec_openapi_json() -> None:
    result = await parse_spec(
        "openapi_json",
        spec_text='{"paths": {"/x": {"get": {"operationId": "getX"}}}}',
    )
    assert result["protocol"] == "openapi_json"
    assert result["tools"][0]["name"] == "getx"


@pytest.mark.anyio
async def test_parse_spec_rejects_unknown_protocol() -> None:
    with pytest.raises(ValueError, match="protocol"):
        await parse_spec("soap", spec_text="{}")


@pytest.mark.anyio
async def test_parse_spec_rejects_empty_openapi() -> None:
    with pytest.raises(ValueError, match="No operations"):
        await parse_spec("openapi_json", spec_text='{"paths": {}}')
