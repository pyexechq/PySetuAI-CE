"""Provider compatibility registry for Universal AI Gateway."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDefinition:
    name: str
    protocol: str
    upstream_key: str
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_structured_output: bool = False


PROVIDER_REGISTRY: dict[str, ProviderDefinition] = {
    "openai": ProviderDefinition("openai", "openai", "openai"),
    "azure_openai": ProviderDefinition("azure_openai", "azure_openai", "openai"),
    "gemini": ProviderDefinition("gemini", "gemini", "gemini"),
    "claude": ProviderDefinition("claude", "anthropic", "claude"),
    "anthropic": ProviderDefinition("anthropic", "anthropic", "claude"),
    "ollama": ProviderDefinition("ollama", "openai-compatible", "ollama"),
    "vllm": ProviderDefinition("vllm", "openai-compatible", "ollama"),
    "deepseek": ProviderDefinition("deepseek", "openai-compatible", "openai"),
}

DEFAULT_COMPATIBILITY_SCORES: dict[tuple[str, str], float] = {
    ("openai", "gemini"): 0.98,
    ("openai", "claude"): 0.96,
    ("openai", "ollama"): 0.92,
    ("openai", "azure_openai"): 0.99,
    ("gemini", "openai"): 0.97,
    ("claude", "openai"): 0.95,
}


def get_provider(name: str) -> ProviderDefinition | None:
    return PROVIDER_REGISTRY.get(name.strip().lower())


def compatibility_score(source_protocol: str, target_provider: str) -> float:
    key = (source_protocol.strip().lower(), target_provider.strip().lower())
    if key in DEFAULT_COMPATIBILITY_SCORES:
        return DEFAULT_COMPATIBILITY_SCORES[key]
    if key[0] == key[1]:
        return 1.0
    return 0.85


def unsupported_features(source_protocol: str, target_provider: str) -> list[str]:
    target = get_provider(target_provider)
    if target is None:
        return ["Unknown target provider"]
    missing: list[str] = []
    if source_protocol == "openai" and target.protocol == "gemini":
        missing.extend(["Function calling parity", "Structured outputs"])
    if target_provider in {"ollama", "vllm"}:
        missing.extend(["Reasoning models", "Native tool schemas"])
    return missing
