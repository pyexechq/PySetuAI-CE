from app.services.gateway_service import coerce_upstream
from app.services.integration_service import GatewayConfig


def test_coerce_upstream_falls_back_to_mock_without_credentials() -> None:
    config = GatewayConfig(
        openai_api_key=None,
        gemini_api_key=None,
        gemini_default_model="gemini-1.5-pro",
        ollama_enabled=False,
        ollama_base_url="http://localhost:11434",
        ollama_default_model="llama3.2",
        source="environment",
    )
    assert coerce_upstream("gemini", config, "gpt-4o", "GPT-4o") == "mock"


def test_coerce_upstream_keeps_openai_when_key_present() -> None:
    config = GatewayConfig(
        openai_api_key="sk-test",
        gemini_api_key=None,
        gemini_default_model="gemini-1.5-pro",
        ollama_enabled=False,
        ollama_base_url="http://localhost:11434",
        ollama_default_model="llama3.2",
        source="environment",
    )
    assert coerce_upstream("openai", config, "gpt-4o", "GPT-4o") == "openai"
