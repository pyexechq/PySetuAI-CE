import os
from typing import Any

from app.schemas.openai import ChatMessage
from app.services.http_client_pool import get_http_client

SUPPORTED_VERTEX_REGIONS = {"us-central1", "europe-west3", "asia-south1"}
DEFAULT_VERTEX_REGION = "us-central1"
DEFAULT_VERTEX_MODEL = "gemini-1.5-pro"


def resolve_vertex_endpoint(
    region: str | None = None,
    project_id: str | None = None,
    model_id: str | None = None,
) -> tuple[str, str]:
    effective_region = region if region in SUPPORTED_VERTEX_REGIONS else DEFAULT_VERTEX_REGION
    effective_project = project_id or os.getenv("GCP_PROJECT_ID", "pysetu-ai-project")
    effective_model = model_id or DEFAULT_VERTEX_MODEL

    url = (
        f"https://{effective_region}-aiplatform.googleapis.com/v1/projects/{effective_project}"
        f"/locations/{effective_region}/publishers/google/models/{effective_model}:generateContent"
    )
    return url, effective_region


def format_vertex_payload(
    messages: list[ChatMessage],
    temperature: float | None = 0.7,
) -> dict[str, Any]:
    contents = []
    for msg in messages:
        role = "user" if msg.role in ("user", "system") else "model"
        contents.append({"role": role, "parts": [{"text": msg.content}]})

    return {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature or 0.7,
            "maxOutputTokens": 1000,
        },
    }


async def call_vertex_regional(
    messages: list[ChatMessage],
    region: str = "us-central1",
    project_id: str | None = None,
    model_id: str = DEFAULT_VERTEX_MODEL,
    temperature: float | None = 0.7,
    gcp_auth_token: str | None = None,
) -> tuple[str, str, str]:
    url, effective_region = resolve_vertex_endpoint(region, project_id, model_id)
    payload = format_vertex_payload(messages, temperature=temperature)

    token = gcp_auth_token or os.getenv("GCP_AUTH_TOKEN", "mock-gcp-token")

    if token.startswith("mock"):
        prompt_text = " ".join(m.content for m in messages)
        response_text = f"[GCP Vertex AI ({effective_region} / {model_id})]: Response for '{prompt_text[:30]}...'"
        return response_text, model_id, effective_region

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    client = await get_http_client()
    res = await client.post(url, json=payload, headers=headers, timeout=60.0)
    res.raise_for_status()
    data = res.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return "", model_id, effective_region
    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    return text, model_id, effective_region
