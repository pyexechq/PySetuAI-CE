"""Unit tests for the local MCP gateway."""

from __future__ import annotations

import io
import json
import unittest

from pysetu_agent.discovery import DiscoveredMcpServer
from pysetu_agent.mcp_gateway import (
    McpServerPool,
    decide_tool_call,
    decide_tool_response,
    gateway_config,
    handle_message,
    handle_tool_call,
    read_http_message,
    read_message,
    run_gateway,
    run_multiplex_gateway,
    write_gateway_config,
    write_http_message,
    write_message,
)
from pysetu_agent.policy import LocalPolicy

SERVER = DiscoveredMcpServer(name="github", source="test", command="npx", args=("-y", "server-github"))


class FakeServer:
    """In-memory stand-in for McpServerProcess."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.written = []
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def write(self, message):
        self.written.append(message)

    def read(self):
        return self.responses.pop(0) if self.responses else None

    def stop(self):
        self.stopped = True


class FramingTest(unittest.TestCase):
    def test_read_write_roundtrip(self) -> None:
        stream = io.StringIO()
        write_message(stream, {"jsonrpc": "2.0", "id": 1, "method": "ping"})
        stream.seek(0)
        self.assertEqual(read_message(stream), {"jsonrpc": "2.0", "id": 1, "method": "ping"})

    def test_read_skips_blank_lines_and_returns_none_on_eof(self) -> None:
        stream = io.StringIO("\n\n")
        self.assertIsNone(read_message(stream))

    def test_http_framing_roundtrip(self) -> None:
        stream = io.StringIO()
        write_http_message(stream, {"jsonrpc": "2.0", "id": 2, "result": {"ok": True}})
        stream.seek(0)
        self.assertEqual(read_http_message(stream), {"jsonrpc": "2.0", "id": 2, "result": {"ok": True}})


class DecideToolCallTest(unittest.TestCase):
    def test_blocks_secret(self) -> None:
        decision = decide_tool_call("github", "create_issue", {"token": "AKIAIOSFODNN7EXAMPLE"}, LocalPolicy.defaults())
        self.assertEqual(decision.action, "block")

    def test_redacts_pii(self) -> None:
        decision = decide_tool_call("github", "create_issue", {"email": "john@example.com"}, LocalPolicy.defaults())
        self.assertEqual(decision.action, "redact")
        self.assertIsNotNone(decision.redacted_arguments)
        self.assertNotIn("john@example.com", json.dumps(decision.redacted_arguments))

    def test_allows_clean(self) -> None:
        decision = decide_tool_call("github", "create_issue", {"title": "hello"}, LocalPolicy.defaults())
        self.assertEqual(decision.action, "allow")

    def test_redaction_invalid_json_falls_back_to_block(self) -> None:
        # Inject a detector whose redaction produces invalid JSON -> block, never forward.
        from pysetu_agent.detection import ScanResult

        def bad_detector(_content):
            return ScanResult(
                classifications=["SSN"],
                redacted_content='{"ssn": [REDACTED]}',  # invalid JSON
                match_count=1,
            )

        decision = decide_tool_call("github", "set", {"ssn": "123-45-6789"}, LocalPolicy.defaults(), detector=bad_detector)
        self.assertEqual(decision.action, "block")


class DecideToolResponseTest(unittest.TestCase):
    def test_redacts_pii_in_text_block(self) -> None:
        result = {"content": [{"type": "text", "text": "Customer email is john@example.com"}]}
        decision = decide_tool_response("github", "get_user", result, LocalPolicy.defaults())
        self.assertEqual(decision.action, "redact")
        self.assertIsNotNone(decision.redacted_result)
        text = decision.redacted_result["content"][0]["text"]
        self.assertNotIn("john@example.com", text)
        self.assertIn("[REDACTED]", text)

    def test_redacts_resource_text_block(self) -> None:
        result = {
            "content": [
                {"type": "resource", "resource": {"uri": "db://hr", "text": "SSN 123-45-6789"}}
            ]
        }
        decision = decide_tool_response("hr", "query", result, LocalPolicy.defaults())
        self.assertEqual(decision.action, "redact")
        text = decision.redacted_result["content"][0]["resource"]["text"]
        self.assertNotIn("123-45-6789", text)

    def test_blocks_secret_in_response(self) -> None:
        result = {"content": [{"type": "text", "text": "key: AKIAIOSFODNN7EXAMPLE"}]}
        decision = decide_tool_response("github", "get_secret", result, LocalPolicy.defaults())
        self.assertEqual(decision.action, "block")

    def test_allows_clean_response(self) -> None:
        result = {"content": [{"type": "text", "text": "All good"}]}
        decision = decide_tool_response("github", "get_user", result, LocalPolicy.defaults())
        self.assertEqual(decision.action, "allow")

    def test_allows_when_no_text_blocks(self) -> None:
        decision = decide_tool_response("github", "get_user", {"ok": True}, LocalPolicy.defaults())
        self.assertEqual(decision.action, "allow")

    def test_does_not_mutate_original_result(self) -> None:
        result = {"content": [{"type": "text", "text": "email john@example.com"}]}
        decide_tool_response("github", "get_user", result, LocalPolicy.defaults())
        self.assertIn("john@example.com", result["content"][0]["text"])


class HandleToolCallResponseRedactionTest(unittest.TestCase):
    def test_redacts_sensitive_response_before_returning(self) -> None:
        upstream = FakeServer(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"content": [{"type": "text", "text": "email john@example.com"}]},
                }
            ]
        )
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "get_user", "arguments": {"id": 1}},
        }
        response = handle_tool_call(message, SERVER, LocalPolicy.defaults(), upstream)
        text = response["result"]["content"][0]["text"]
        self.assertNotIn("john@example.com", text)
        self.assertIn("[REDACTED]", text)

    def test_redact_responses_false_passes_through(self) -> None:
        upstream = FakeServer(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"content": [{"type": "text", "text": "email john@example.com"}]},
                }
            ]
        )
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "get_user", "arguments": {"id": 1}},
        }
        response = handle_tool_call(
            message, SERVER, LocalPolicy.defaults(), upstream, redact_responses=False
        )
        self.assertIn("john@example.com", response["result"]["content"][0]["text"])

    def test_blocks_sensitive_response(self) -> None:
        upstream = FakeServer(
            [
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "result": {"content": [{"type": "text", "text": "token AKIAIOSFODNN7EXAMPLE"}]},
                }
            ]
        )
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "get_secret", "arguments": {}},
        }
        response = handle_tool_call(message, SERVER, LocalPolicy.defaults(), upstream)
        self.assertIn("error", response)


class HandleToolCallTest(unittest.TestCase):
    def test_block_returns_error_and_does_not_call_upstream(self) -> None:
        upstream = FakeServer([])
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "create_issue", "arguments": {"token": "AKIAIOSFODNN7EXAMPLE"}},
        }
        response = handle_tool_call(message, SERVER, LocalPolicy.defaults(), upstream)
        self.assertIn("error", response)
        self.assertEqual(upstream.written, [])

    def test_redact_forwards_modified_args(self) -> None:
        upstream = FakeServer([{"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}])
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "create_issue", "arguments": {"email": "john@example.com"}},
        }
        response = handle_tool_call(message, SERVER, LocalPolicy.defaults(), upstream)
        self.assertEqual(response["result"], {"ok": True})
        self.assertEqual(len(upstream.written), 1)
        forwarded = upstream.written[0]["params"]["arguments"]
        self.assertNotIn("john@example.com", json.dumps(forwarded))

    def test_allow_forwards_unchanged(self) -> None:
        upstream = FakeServer([{"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}])
        message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "create_issue", "arguments": {"title": "hello"}},
        }
        response = handle_tool_call(message, SERVER, LocalPolicy.defaults(), upstream)
        self.assertEqual(response["result"], {"ok": True})
        self.assertEqual(upstream.written[0]["params"]["arguments"], {"title": "hello"})


class HandleMessageTest(unittest.TestCase):
    def test_tools_list_passed_through(self) -> None:
        upstream = FakeServer([{"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}])
        message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        response = handle_message(message, SERVER, LocalPolicy.defaults(), upstream)
        self.assertEqual(response["result"], {"tools": []})

    def test_notification_forwarded_with_no_response(self) -> None:
        upstream = FakeServer([])
        message = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        response = handle_message(message, SERVER, LocalPolicy.defaults(), upstream)
        self.assertIsNone(response)
        self.assertEqual(upstream.written[0]["method"], "notifications/initialized")


class RunGatewayTest(unittest.TestCase):
    def test_end_to_end_proxy(self) -> None:
        reader = io.StringIO(
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
            + "\n"
            + json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "create_issue", "arguments": {"token": "AKIAIOSFODNN7EXAMPLE"}},
                }
            )
            + "\n"
            + json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "create_issue", "arguments": {"title": "hello"}},
                }
            )
            + "\n"
        )
        writer = io.StringIO()
        upstream = FakeServer(
            [
                {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "real"}}},
                {"jsonrpc": "2.0", "id": 3, "result": {"ok": True}},
            ]
        )
        code = run_gateway(SERVER, LocalPolicy.defaults(), reader=reader, writer=writer, server_factory=lambda _s: upstream)
        self.assertEqual(code, 0)
        self.assertTrue(upstream.started)
        self.assertTrue(upstream.stopped)
        output = writer.getvalue().strip().split("\n")
        self.assertEqual(len(output), 3)
        # initialize passed through
        self.assertIn("serverInfo", output[0])
        # blocked tool call -> error
        self.assertIn("error", output[1])
        # clean tool call -> result
        self.assertIn("ok", output[2])


class McpServerPoolTest(unittest.TestCase):
    def test_pool_starts_and_stops_all(self) -> None:
        server2 = DiscoveredMcpServer(name="hr", source="test", command="npx", args=("-y", "server-hr"))
        pool = McpServerPool([SERVER, server2], server_factory=lambda _s: FakeServer([]))
        pool.start()
        self.assertTrue(pool.get("github").started)
        self.assertTrue(pool.get("hr").started)
        self.assertEqual(pool.default_name(), "github")
        self.assertEqual(pool.names(), ["github", "hr"])
        pool.stop()
        self.assertTrue(pool.get("github").stopped)
        self.assertTrue(pool.get("hr").stopped)

    def test_pool_unknown_server_returns_none(self) -> None:
        pool = McpServerPool([SERVER], server_factory=lambda _s: FakeServer([]))
        self.assertIsNone(pool.get("nope"))
        self.assertIsNone(pool.server("nope"))


class RunMultiplexGatewayTest(unittest.TestCase):
    def test_routes_by_server_field(self) -> None:
        server2 = DiscoveredMcpServer(name="hr", source="test", command="npx", args=("-y", "server-hr"))
        reader = io.StringIO(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "server": "github",
                    "method": "tools/call",
                    "params": {"name": "create_issue", "arguments": {"title": "hello"}},
                }
            )
            + "\n"
            + json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "server": "hr",
                    "method": "tools/call",
                    "params": {"name": "query", "arguments": {"q": "all"}},
                }
            )
            + "\n"
        )
        writer = io.StringIO()
        upstreams = {
            "github": FakeServer([{"jsonrpc": "2.0", "id": 1, "result": {"ok": "gh"}}]),
            "hr": FakeServer([{"jsonrpc": "2.0", "id": 2, "result": {"ok": "hr"}}]),
        }

        def factory(server):
            return upstreams[server.name]

        code = run_multiplex_gateway(
            [SERVER, server2], LocalPolicy.defaults(), reader=reader, writer=writer, server_factory=factory
        )
        self.assertEqual(code, 0)
        self.assertTrue(upstreams["github"].started)
        self.assertTrue(upstreams["hr"].started)
        self.assertTrue(upstreams["github"].stopped)
        self.assertTrue(upstreams["hr"].stopped)
        output = writer.getvalue().strip().split("\n")
        self.assertEqual(len(output), 2)
        self.assertIn("gh", output[0])
        self.assertIn("hr", output[1])

    def test_unknown_server_returns_error(self) -> None:
        reader = io.StringIO(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "server": "nope",
                    "method": "tools/call",
                    "params": {"name": "x", "arguments": {}},
                }
            )
            + "\n"
        )
        writer = io.StringIO()
        code = run_multiplex_gateway(
            [SERVER], LocalPolicy.defaults(), reader=reader, writer=writer, server_factory=lambda _s: FakeServer([])
        )
        self.assertEqual(code, 0)
        output = writer.getvalue().strip()
        self.assertIn("error", output)
        self.assertIn("unknown MCP server", output)

    def test_defaults_to_first_server_without_server_field(self) -> None:
        reader = io.StringIO(
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "create_issue", "arguments": {"title": "hello"}},
                }
            )
            + "\n"
        )
        writer = io.StringIO()
        upstream = FakeServer([{"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}])
        code = run_multiplex_gateway(
            [SERVER], LocalPolicy.defaults(), reader=reader, writer=writer, server_factory=lambda _s: upstream
        )
        self.assertEqual(code, 0)
        self.assertIn("ok", writer.getvalue())


class GatewayConfigTest(unittest.TestCase):
    def test_maps_stdio_servers_and_skips_http(self) -> None:
        http_server = DiscoveredMcpServer(name="remote", source="test", url="https://example.com", transport="http")
        config = gateway_config([SERVER, http_server], launcher="/usr/bin/python3")
        self.assertIn("github", config["mcpServers"])
        self.assertNotIn("remote", config["mcpServers"])
        entry = config["mcpServers"]["github"]
        self.assertEqual(entry["command"], "/usr/bin/python3")
        self.assertIn("--server", entry["args"])
        self.assertIn("github", entry["args"])

    def test_write_gateway_config(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, ".mcp.json")
            write_gateway_config(str(path), [SERVER], launcher="/usr/bin/python3")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("mcpServers", data)
            self.assertIn("github", data["mcpServers"])


if __name__ == "__main__":
    unittest.main()
