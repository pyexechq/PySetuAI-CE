import pytest

from app.schemas.openai import ChatMessage
from app.services.regional_adapters.bedrock_adapter import (
    call_bedrock_regional,
    format_bedrock_payload,
    resolve_bedrock_endpoint,
)
from app.services.regional_adapters.vertex_adapter import (
    call_vertex_regional,
    format_vertex_payload,
    resolve_vertex_endpoint,
)


def test_resolve_bedrock_endpoint_supported_regions():
    url, region = resolve_bedrock_endpoint("ap-south-1", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    assert region == "ap-south-1"
    assert "bedrock-runtime.ap-south-1.amazonaws.com" in url

    url_fallback, region_fallback = resolve_bedrock_endpoint("invalid-region")
    assert region_fallback == "us-east-1"


def test_format_bedrock_payload():
    messages = [ChatMessage(role="user", content="Hello Bedrock")]
    payload = format_bedrock_payload(messages, temperature=0.5)
    assert payload["anthropic_version"] == "bedrock-2023-05-31"
    assert payload["temperature"] == 0.5
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["content"] == "Hello Bedrock"


@pytest.mark.anyio
async def test_call_bedrock_regional_mock():
    messages = [ChatMessage(role="user", content="Hello Bedrock regional")]
    text, model, region = await call_bedrock_regional(messages, region="eu-central-1")
    assert region == "eu-central-1"
    assert "[AWS Bedrock" in text


def test_resolve_vertex_endpoint_supported_regions():
    url, region = resolve_vertex_endpoint("asia-south1", "my-project", "gemini-1.5-pro")
    assert region == "asia-south1"
    assert "asia-south1-aiplatform.googleapis.com" in url
    assert "my-project" in url


def test_format_vertex_payload():
    messages = [ChatMessage(role="user", content="Hello Vertex")]
    payload = format_vertex_payload(messages, temperature=0.2)
    assert payload["generationConfig"]["temperature"] == 0.2
    assert len(payload["contents"]) == 1
    assert payload["contents"][0]["parts"][0]["text"] == "Hello Vertex"


@pytest.mark.anyio
async def test_call_vertex_regional_mock():
    messages = [ChatMessage(role="user", content="Hello Vertex regional")]
    text, model, region = await call_vertex_regional(messages, region="asia-south1")
    assert region == "asia-south1"
    assert "[GCP Vertex AI" in text
