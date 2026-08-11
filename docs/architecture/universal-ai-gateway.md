# Universal AI Gateway (UAG)

**Last Updated:** Aug 11, 2026

## Overview

The Universal AI Gateway (UAG) lets applications built for one AI provider transparently consume another provider without code changes. HelixGuard performs protocol translation, governance enforcement, auditing, and intelligent routing.

Examples:

- OpenAI client → Gemini, Claude, Ollama, DeepSeek, Azure OpenAI
- Gemini client → OpenAI
- Claude client → OpenAI

## Core principle

**Governance always executes before translation.**

### Request flow

```text
Application → UAG → Authentication → Policy Engine → Data Classification
→ PII Detection → DLP Engine → Risk Assessment → Protocol Translation
→ LLM Router → Target Model
```

### Response flow

```text
Target Model → Response Translation → Output Governance → PII Detection
→ Compliance Checks → Audit Logging → Application
```

## Module layout

```text
backend/app/modules/uag/
├── canonical.py              # CanonicalPrompt, TranslationTrace
├── protocol_translator.py    # ProtocolTranslator orchestrator
├── provider_registry.py      # Provider compatibility registry
├── model_mapping.py          # Tenant model alias resolution
├── translation_policy.py     # Provider translation policies
├── service.py                # Pre/post governance pipeline hooks
└── translators/              # OpenAI, Gemini, Claude, Azure OpenAI
```

## Canonical request model

All incoming requests normalize to `CanonicalPrompt` before governance engines run. Fields include `tenant_id`, `request_id`, `source_protocol`, `target_provider`, `model`, `requested_model`, `messages`, `tools`, `system_prompt`, `temperature`, `max_tokens`, and `metadata`.

## Admin surfaces

| Surface | Path | Purpose |
|---------|------|---------|
| Compatibility Center | `/compatibility-center` | Model mappings, stats, translation policies |
| Studio | `/studio` → Translation Simulator | Preview request → canonical → translated payload |
| Dashboard | `/` | UAG KPIs and route breakdown |
| Audit Explorer | `/audit-explorer` | Translation trace on governed requests |

## Security

Translation never bypasses policy engine, DLP, PII detection, redaction, compliance controls, or audit logging. All translated requests remain auditable via `UagTranslationEvent` and audit log `uag_trace` metadata.

## Air-gapped support

Applications may request `gpt-4o` while HelixGuard routes to Llama, Qwen, or Granite through model mappings and translation policies alone.
