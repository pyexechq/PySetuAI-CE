import os
from typing import Any
import httpx

from app.schemas.openai import ChatMessage

SUPPORTED_BEDROCK_REGIONS = {"us-east-1", "eu-central-1", "ap-south-1"}
DEFAULT_BEDROCK_REGION = "us-east-1"
DEFAULT_BEDROCK_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"


def resolve_bedrock_endpoint(region: str | None = None, model_id: str | None = None) -> tuple[str, str]:
    effective_region = region if region in SUPPORTED_BEDROCK_REGIONS else DEFAULT_BEDROCK_REGION
    effective_model = model_id or DEFAULT_BEDROCK_MODEL
    url = f"https://bedrock-runtime.{effective_region}.amazonaws.com/model/{effective_model}/invoke"
    return url, effective_region


def format_bedrock_payload(
    messages: list[ChatMessage],
    temperature: float | None = 0.7,
    max_tokens: int = 1000,
) -> dict[str, Any]:
    formatted_messages = []
    for msg in messages:
        role = "user" if msg.role in ("user", "system") else "assistant"
        formatted_messages.append({"role": role, "content": msg.content})

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature or 0.7,
        "messages": formatted_messages,
    }


async def call_bedrock_regional(
    messages: list[ChatMessage],
    region: str = "us-east-1",
    model_id: str = DEFAULT_BEDROCK_MODEL,
    temperature: float | None = 0.7,
    aws_access_key: str | None = None,
    aws_secret_key: str | None = None,
) -> tuple[str, str, str]:
    url, effective_region = resolve_bedrock_endpoint(region, model_id)
    payload = format_bedrock_payload(messages, temperature=temperature)

    access_key = aws_access_key or os.getenv("AWS_ACCESS_KEY_ID", "mock-aws-key")
    secret_key = aws_secret_key or os.getenv("AWS_SECRET_ACCESS_KEY", "mock-aws-secret")

    # If keys are mock credentials or in dev/test environment, return sample translated response
    if access_key.startswith("mock") or secret_key.startswith("mock"):
        prompt_text = " ".join(m.content for m in messages)
        response_text = f"[AWS Bedrock ({effective_region} / {model_id})]: Response for '{prompt_text[:30]}...'"
        return response_text, model_id, effective_region

    headers = {
        "Content-Type": "application/json",
        "X-Amz-Target": f"AmazonBedrockControlPlane.{model_id}",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(url, json=payload, headers=headers)
        res.raise_for_status()
        data = res.json()
        content = data.get("content", [{}])[0].get("text", "")
        return content, model_id, effective_region
