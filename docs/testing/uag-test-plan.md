# UAG Test Plan

**Last Updated:** Aug 11, 2026

## Functional tests

| ID | Scenario | Expected |
|----|----------|----------|
| UAG-F01 | OpenAI → Gemini translation | Gemini `contents` payload with system instruction |
| UAG-F02 | OpenAI → Claude translation | Anthropic messages + system block |
| UAG-F03 | OpenAI → Ollama via mapping | Model alias resolves to local model |
| UAG-F04 | Gemini → OpenAI response passthrough | Caller sees requested model ID |
| UAG-F05 | Simulate API | Returns original, canonical, translated, trace |
| UAG-F06 | Translation policy match | Routing context overrides provider |

## Security tests

| ID | Scenario | Expected |
|----|----------|----------|
| UAG-S01 | PII in canonical prompt | `text_for_inspection()` includes user content for DLP |
| UAG-S02 | Secret patterns in messages | Governed before upstream translation |
| UAG-S03 | Audit trace | UAG events recorded with governance actions |
| UAG-S04 | Policy bypass attempt | Translation cannot skip policy engine |

## Performance targets

| Stage | Target |
|-------|--------|
| Protocol translation | < 50 ms |
| Routing | < 100 ms |
| Governance (full pipeline) | < 100 ms |

Automated coverage: `backend/tests/test_uag.py`

## Manual QA

1. Open Compatibility Center — verify seeded mappings for `acme` tenant
2. Studio → Translation Simulator — run `gpt-4o` simulation
3. Dashboard — confirm UAG KPI row when translation events exist
4. Audit Explorer — select LLM request with UAG detail; verify translation trace panel
