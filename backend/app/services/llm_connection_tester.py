import time
import uuid
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.governance import LLMProvider
from app.services.secrets_service import get_provider_secret


async def test_llm_provider_connection(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    provider_type: str,
    api_key: str | None = None,
    endpoint_url: str | None = None,
    provider_id: str | None = None,
) -> tuple[bool, str, float | None, list[str] | None]:
    """
    Tests live upstream connectivity and authentication for an LLM provider.
    Returns (success, message, latency_ms, models_found).
    """
    p_type = (provider_type or "openai").lower().strip()
    key = (api_key or "").strip()
    endpoint = (endpoint_url or "").strip()

    # If key wasn't supplied, attempt to read stored key for existing provider
    if not key and provider_id:
        try:
            p_uuid = uuid.UUID(provider_id)
            provider = await db.get(LLMProvider, p_uuid)
            if provider and provider.tenant_id == tenant_id:
                stored = await get_provider_secret(db, tenant_id, provider)
                if stored:
                    key = stored.strip()
        except Exception:
            pass

    start_time = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            if p_type == "openai":
                if not key:
                    return False, "API key is required to test connection with OpenAI.", None, None

                base_url = endpoint if endpoint else "https://api.openai.com/v1"
                base_url = base_url.rstrip("/")
                if not base_url.endswith("/v1") and "api.openai.com" in base_url:
                    base_url = f"{base_url}/v1"

                url = f"{base_url}/models"
                res = await client.get(url, headers={"Authorization": f"Bearer {key}"})
                latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
                    return True, f"Successfully authenticated with OpenAI API (HTTP 200, {latency_ms}ms).", latency_ms, models[:10]
                elif res.status_code == 401:
                    return False, "Authentication failed: Invalid OpenAI API key (HTTP 401).", latency_ms, None
                elif res.status_code == 429:
                    return False, "OpenAI rate limit or quota exceeded (HTTP 429).", latency_ms, None
                else:
                    return False, f"OpenAI returned error HTTP {res.status_code}: {res.text[:150]}", latency_ms, None

            elif p_type == "gemini":
                if not key:
                    return False, "API key is required to test connection with Google Gemini.", None, None

                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                res = await client.get(url)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name", "").replace("models/", "") for m in data.get("models", []) if isinstance(m, dict)]
                    return True, f"Successfully authenticated with Google Gemini API (HTTP 200, {latency_ms}ms).", latency_ms, models[:10]
                elif res.status_code in (400, 403):
                    return False, "Authentication failed: Invalid Google Gemini API key.", latency_ms, None
                elif res.status_code == 429:
                    return False, "Gemini rate limit or quota exceeded (HTTP 429).", latency_ms, None
                else:
                    return False, f"Gemini API returned error HTTP {res.status_code}: {res.text[:150]}", latency_ms, None

            elif p_type == "anthropic":
                if not key:
                    return False, "API key is required to test connection with Anthropic.", None, None

                url = "https://api.anthropic.com/v1/models"
                headers = {
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                }
                res = await client.get(url, headers=headers)
                latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
                    return True, f"Successfully authenticated with Anthropic API (HTTP 200, {latency_ms}ms).", latency_ms, models[:10]
                elif res.status_code == 401:
                    return False, "Authentication failed: Invalid Anthropic API key (HTTP 401).", latency_ms, None
                else:
                    return False, f"Anthropic API returned HTTP {res.status_code}: {res.text[:150]}", latency_ms, None

            elif p_type == "ollama":
                target_url = endpoint or "http://localhost:11434"
                target_url = target_url.rstrip("/")
                res = await client.get(f"{target_url}/api/tags")
                latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", []) if isinstance(m, dict)]
                    return True, f"Successfully connected to Ollama host at {target_url} ({latency_ms}ms).", latency_ms, models
                else:
                    return False, f"Ollama host returned HTTP {res.status_code}", latency_ms, None

            elif p_type in ("azure", "custom"):
                if not endpoint:
                    return False, "Endpoint URL is required for custom/azure provider.", None, None
                if not endpoint.startswith(("http://", "https://")):
                    return False, "Endpoint URL must start with http:// or https://", None, None

                headers = {}
                if key:
                    headers["Authorization"] = f"Bearer {key}"
                    headers["api-key"] = key

                # Try GET or HEAD
                try:
                    res = await client.get(endpoint, headers=headers)
                except Exception:
                    res = await client.head(endpoint, headers=headers)

                latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
                if res.status_code in (200, 204, 404, 405):  # Host reachable
                    return True, f"Endpoint is reachable (HTTP {res.status_code}, {latency_ms}ms).", latency_ms, None
                elif res.status_code in (401, 403):
                    return False, f"Authentication rejected by endpoint (HTTP {res.status_code}). Check your API key.", latency_ms, None
                else:
                    return False, f"Endpoint returned HTTP {res.status_code}", latency_ms, None

            else:
                return False, f"Unsupported provider type: {p_type}", None, None

    except httpx.ConnectError:
        return False, f"Failed to establish network connection to {p_type} endpoint.", None, None
    except httpx.TimeoutException:
        return False, f"Connection to {p_type} endpoint timed out after 10 seconds.", None, None
    except Exception as exc:
        return False, f"Connection error: {str(exc)}", None, None
