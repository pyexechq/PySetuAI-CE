from types import SimpleNamespace

from app.services.gateway_service import PreparedChat, coerce_upstream, resolve_openai_api_key
from app.services.integration_service import GatewayConfig


def _config(openai_key: str | None = None) -> GatewayConfig:
    return GatewayConfig(
        openai_api_key=openai_key,
        gemini_api_key=None,
        gemini_default_model="gemini-1.5-pro",
        ollama_enabled=False,
        ollama_base_url="http://localhost:11434",
        ollama_default_model="llama3.2",
        source="environment",
    )


def test_coerce_upstream_uses_ingress_bearer_without_config_key() -> None:
    config = _config(None)
    assert (
        coerce_upstream("openai", config, "gpt-4o", "gpt-4o", ingress_bearer_token="sk-pass-through")
        == "openai"
    )


def test_resolve_openai_api_key_prefers_ingress_token() -> None:
    prepared = PreparedChat(
        messages=[],
        routed_model="gpt-4o",
        upstream="openai",
        config=_config("sk-config"),
        ingress=SimpleNamespace(),
        combined="",
        ingress_bearer_token="sk-pass-through",
    )
    assert resolve_openai_api_key(prepared) == "sk-pass-through"


def test_resolve_openai_api_key_falls_back_to_config() -> None:
    prepared = PreparedChat(
        messages=[],
        routed_model="gpt-4o",
        upstream="openai",
        config=_config("sk-config"),
        ingress=SimpleNamespace(),
        combined="",
        ingress_bearer_token=None,
    )
    assert resolve_openai_api_key(prepared) == "sk-config"
