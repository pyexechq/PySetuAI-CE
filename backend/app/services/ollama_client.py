import httpx

from app.config import settings


class OllamaError(Exception):
    pass


async def list_ollama_models(base_url: str | None = None) -> list[str]:
    url_base = (base_url or settings.ollama_base_url).rstrip("/")
    url = f"{url_base}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
    except httpx.HTTPError as exc:
        raise OllamaError(f"Cannot reach Ollama at {url_base}: {exc}") from exc


async def check_ollama_health(base_url: str | None = None, default_model: str | None = None) -> dict:
    resolved_base = base_url or settings.ollama_base_url
    resolved_model = default_model or settings.ollama_default_model
    try:
        models = await list_ollama_models(resolved_base)
        return {
            "reachable": True,
            "base_url": resolved_base,
            "models": models,
            "default_model": resolved_model,
        }
    except OllamaError as exc:
        return {
            "reachable": False,
            "base_url": resolved_base,
            "error": str(exc),
            "models": [],
            "default_model": resolved_model,
        }


def resolve_ollama_model(requested: str, available: list[str], default_model: str | None = None) -> str:
    fallback = default_model or settings.ollama_default_model
    if not available:
        return fallback

    normalized = requested.strip().lower().replace(" ", "")

    for name in available:
        candidate = name.lower().replace(" ", "")
        if normalized == candidate or normalized in candidate or candidate.startswith(normalized):
            return name

    aliases = {
        "gpt-4o": fallback,
        "gpt4o": fallback,
        "llama3.170b": fallback,
        "llama3170b": fallback,
        "claude3.5sonnet": fallback,
        "gemini1.5pro": fallback,
    }
    alias = aliases.get(normalized)
    if alias:
        for name in available:
            if name == alias or name.startswith(alias.split(":")[0]):
                return name

    if fallback in available:
        return fallback

    for name in available:
        if fallback.split(":")[0] in name:
            return name

    return available[0]
