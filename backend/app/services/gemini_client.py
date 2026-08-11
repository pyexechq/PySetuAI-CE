import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.schemas.openai import ChatMessage

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiError(Exception):
    pass


def normalize_gemini_model(requested: str, default: str = "gemini-1.5-pro") -> str:
    normalized = requested.strip().lower().replace(" ", "")
    aliases = {
        "gemini1.5pro": "gemini-1.5-pro",
        "gemini-1.5-pro": "gemini-1.5-pro",
        "gemini15pro": "gemini-1.5-pro",
        "gemini2.0flash": "gemini-2.0-flash",
        "gemini-2.0-flash": "gemini-2.0-flash",
        "gemini1.5flash": "gemini-1.5-flash",
    }
    if normalized in aliases:
        return aliases[normalized]
    if normalized.startswith("gemini"):
        return requested.strip()
    return default


def map_messages_to_gemini(messages: list[ChatMessage]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    contents: list[dict[str, Any]] = []
    system_chunks: list[str] = []

    for message in messages:
        if message.role == "system":
            system_chunks.append(message.content)
        elif message.role == "assistant":
            contents.append({"role": "model", "parts": [{"text": message.content}]})
        else:
            contents.append({"role": "user", "parts": [{"text": message.content}]})

    if not contents and system_chunks:
        contents.append({"role": "user", "parts": [{"text": "\n".join(system_chunks)}]})
        system_chunks = []

    system_instruction = {"parts": [{"text": "\n".join(system_chunks)}]} if system_chunks else None
    return contents, system_instruction


async def call_gemini(
    model: str,
    messages: list[ChatMessage],
    api_key: str,
    temperature: float | None = None,
) -> tuple[str, str]:
    contents, system_instruction = map_messages_to_gemini(messages)
    gemini_model = normalize_gemini_model(model)
    payload: dict[str, Any] = {"contents": contents}
    if system_instruction:
        payload["systemInstruction"] = system_instruction
    if temperature is not None:
        payload["generationConfig"] = {"temperature": temperature}

    url = f"{GEMINI_API_BASE}/models/{gemini_model}:generateContent"
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, params={"key": api_key}, json=payload)
        response.raise_for_status()
        data = response.json()

    candidates = data.get("candidates") or []
    if not candidates:
        raise GeminiError("Gemini returned no candidates")
    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts)
    return text, gemini_model


async def stream_gemini(
    model: str,
    messages: list[ChatMessage],
    api_key: str,
    temperature: float | None = None,
) -> AsyncIterator[str]:
    contents, system_instruction = map_messages_to_gemini(messages)
    gemini_model = normalize_gemini_model(model)
    payload: dict[str, Any] = {"contents": contents}
    if system_instruction:
        payload["systemInstruction"] = system_instruction
    if temperature is not None:
        payload["generationConfig"] = {"temperature": temperature}

    url = f"{GEMINI_API_BASE}/models/{gemini_model}:streamGenerateContent"
    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream("POST", url, params={"key": api_key, "alt": "sse"}, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:].strip()
                if not raw or raw == "[DONE]":
                    continue
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                candidates = event.get("candidates") or []
                if not candidates:
                    continue
                parts = candidates[0].get("content", {}).get("parts") or []
                delta = "".join(part.get("text", "") for part in parts)
                if delta:
                    yield delta
