"""Ollama URL resolution for Docker vs localhost tenant defaults."""

from app.services.integration_service import resolve_ollama_base_url


def test_localhost_tenant_url_uses_platform_docker_host(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.integration_service.settings.ollama_base_url",
        "http://host.docker.internal:11434",
    )
    assert (
        resolve_ollama_base_url("http://localhost:11434")
        == "http://host.docker.internal:11434"
    )


def test_custom_tenant_url_is_preserved(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.integration_service.settings.ollama_base_url",
        "http://host.docker.internal:11434",
    )
    assert resolve_ollama_base_url("http://ollama.internal:11434") == "http://ollama.internal:11434"
