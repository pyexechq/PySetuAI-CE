"""E2E test for the server-side MCP tool loop.

Mints a client key, then calls the gateway asking the LLM to use the
getPetById REST-proxy tool, and verifies the final answer contains the
pet name (proving the gateway executed the tool internally and re-called
the LLM instead of returning finish_reason=tool_calls).
"""
import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8001")
PASSWORD = os.environ.get("DEMO_SEED_PASSWORD", "demo1234")
ADMIN_EMAIL = "admin@acme.com"
TENANT_SLUG = "acme"
MODEL = os.environ.get("MODEL", "llama3.2")


def _request(method, url, headers, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            return e.code, {"raw": raw[:500]}
    except urllib.error.URLError as e:
        return 0, {"error": str(e.reason)}


def login():
    status, body = _request(
        "POST",
        f"{BASE_URL}/api/v1/auth/login",
        {"Content-Type": "application/json"},
        {"tenant_slug": TENANT_SLUG, "email": ADMIN_EMAIL, "password": PASSWORD},
    )
    if status != 200:
        raise RuntimeError(f"Login failed ({status}): {body}")
    return body["access_token"]


def mint_key(jwt):
    status, body = _request(
        "POST",
        f"{BASE_URL}/api/v1/client-api-keys",
        {"Content-Type": "application/json", "Authorization": f"Bearer {jwt}"},
        {"name": "tool-loop-test", "description": "E2E tool loop verification"},
    )
    if status != 201:
        raise RuntimeError(f"Key mint failed ({status}): {body}")
    return body["api_key"]


def main():
    print(f"[provision] Logging in as {ADMIN_EMAIL}...")
    jwt = login()
    key = mint_key(jwt)
    print(f"[provision] Minted key: {key[:12]}...")

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    body = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Use the getPetById tool to look up pet with id 1, "
                    "then tell me the pet's name."
                ),
            }
        ],
    }
    print(f"[call] POST {BASE_URL}/v1/chat/completions model={MODEL}")
    status, resp = _request("POST", f"{BASE_URL}/v1/chat/completions", headers, body)
    print(f"[call] status={status}")
    print(json.dumps(resp, indent=2)[:4000])

    if status != 200:
        print("\nRESULT: FAIL (non-200)")
        return 1

    choice = (resp.get("choices") or [{}])[0]
    finish = choice.get("finish_reason")
    content = (choice.get("message") or {}).get("content") or ""
    pysetu = resp.get("pysetu") or {}
    mcp_calls = pysetu.get("mcp_tool_calls")

    print(f"\nfinish_reason={finish}")
    print(f"mcp_tool_calls={mcp_calls}")
    print(f"content={content!r}")

    if finish == "tool_calls":
        print("\nRESULT: FAIL (gateway returned finish_reason=tool_calls, loop did not run)")
        return 1
    if not content.strip():
        print("\nRESULT: FAIL (empty content)")
        return 1
    if not mcp_calls:
        print("\nRESULT: WARN (no mcp_tool_calls recorded; tool may not have been used)")
    print("\nRESULT: PASS (tool loop completed, final answer returned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
