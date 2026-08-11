# Protocol Translation

**Last Updated:** Aug 11, 2026

## Supported protocols

| Direction | Protocols |
|-----------|-----------|
| Input | OpenAI, Gemini, Claude, Azure OpenAI |
| Output | OpenAI, Gemini, Claude, Ollama, vLLM, DeepSeek, Azure OpenAI |

## Translator interface

Each translator in `backend/app/modules/uag/translators/` implements:

- `normalize()` — detect and parse inbound payload
- `translate_to_canonical()` — map provider payload to `CanonicalPrompt`
- `translate_from_canonical()` / `translate_to_upstream()` — build upstream request
- `translate_response()` — map upstream response back to caller protocol

## ProtocolTranslator

```python
class ProtocolTranslator:
    def detect_protocol(path, headers)
    def normalize_request(request, tenant_id)
    def translate_request(canonical) -> (payload, TranslationTrace)
    def translate_response(canonical, upstream_response, trace)
```

## Provider registry

`provider_registry.py` defines upstream keys, wire protocols, and compatibility scores (e.g. OpenAI → Gemini 98%).

## Model mapping

Tenant-scoped mappings in `uag_model_mappings` translate requested model IDs (e.g. `gpt-4o`) to actual upstream models (e.g. `gemini-1.5-pro`).

## Translation policies

`UagTranslationPolicy` rows match routing context tags (department, country, application) and override target provider or emulate protocol:

```yaml
IF department=finance THEN route_to=ollama
IF country=EU THEN route_to=azure_openai
IF application=legacy_app THEN emulate=openai
```

## Unsupported features

Partial parity is tracked per route: tool calling, structured outputs, streaming edge cases, reasoning models.
