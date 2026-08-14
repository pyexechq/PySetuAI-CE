from app.config import settings
from app.services.ai_assist_config_service import (
    AiAssistConfig,
    ALL_PROVIDERS,
    LOCAL_PROVIDERS,
    supported_ai_assist_providers,
)


def test_ai_assist_unavailable_without_key() -> None:
    config = AiAssistConfig(
        enabled=True,
        provider="openai",
        model="gpt-4o-mini",
        api_key=None,
        base_url=None,
        source="none",
    )
    assert config.available is False


def test_ai_assist_available_with_key() -> None:
    config = AiAssistConfig(
        enabled=True,
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-test-key",
        base_url=None,
        source="tenant_settings",
    )
    assert config.available is True


def test_ai_assist_ollama_available_without_key() -> None:
    config = AiAssistConfig(
        enabled=True,
        provider="ollama",
        model="llama3.2",
        api_key=None,
        base_url="http://localhost:11434",
        source="tenant_settings",
    )
    assert config.available is True


def test_ai_assist_groq_requires_key() -> None:
    config = AiAssistConfig(
        enabled=True,
        provider="groq",
        model="llama-3.1-8b-instant",
        api_key=None,
        base_url="https://api.groq.com/openai/v1",
        source="none",
    )
    assert config.available is False


def test_supported_providers_in_air_gap_mode(monkeypatch) -> None:
    monkeypatch.setattr(settings, "air_gap_mode", True)
    supported = supported_ai_assist_providers()
    assert set(supported) == LOCAL_PROVIDERS
    assert "openai" not in supported


def test_all_providers_when_not_air_gap(monkeypatch) -> None:
    monkeypatch.setattr(settings, "air_gap_mode", False)
    assert set(supported_ai_assist_providers()) == ALL_PROVIDERS
