from app.services.ai_assist_config_service import AiAssistConfig, resolve_ai_assist_config


def test_ai_assist_unavailable_without_key() -> None:
    config = AiAssistConfig(
        enabled=True,
        provider="openai",
        model="gpt-4o-mini",
        api_key=None,
        source="none",
    )
    assert config.available is False


def test_ai_assist_available_with_key() -> None:
    config = AiAssistConfig(
        enabled=True,
        provider="openai",
        model="gpt-4o-mini",
        api_key="sk-test-key",
        source="tenant_settings",
    )
    assert config.available is True
