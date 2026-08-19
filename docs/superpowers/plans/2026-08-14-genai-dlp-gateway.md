# GenAI DLP Gateway — Implementation Plan

> **Status:** Complete (Aug 14, 2026). Backlog IDs **BL-109–BL-115**.

**Goal:** Extend PySetu from LLM ingress DLP to a governed data-movement control plane with sensitivity labels, OPA enforcement for vector destinations, RAG gateway, evidence bundles, and break-glass exemptions.

**Architecture:** DLP scan → sensitivity mapping → OPA input (`data` + `movement`) → allow/deny → audit + evidence JSON.

**Tech stack:** Python/FastAPI, OPA/Rego, existing `dlp_service` + `opa_service` + `gateway_service`.

---

## Phase 1: DLP v2 — Sensitivity labels ✅

- [x] `dlp_classification.py` — `ENTITY_TO_SENSITIVITY`, `derive_sensitivity_labels()`, `highest_sensitivity()`
- [x] Extended `DlpScanResult` with sensitivity fields
- [x] Scan API returns sensitivity labels
- [x] Tests: `test_dlp_classification.py`

## Phase 2: OPA data-movement ✅

- [x] `build_data_movement_opa_input()` + `data`/`movement` blocks in OPA input
- [x] Rego rules block restricted labels → vector destinations
- [x] `data_movement_service.py` — DLP + OPA evaluation
- [x] Gateway wiring for sensitivity in audit detail
- [x] Tests: `test_opa_data_movement.py`

## Phase 3: RAG gateway ✅

- [x] `POST /rag-gateway/evaluate`, `/upsert`, `/ingest`
- [x] `embedding_service.py`, `pinecone_adapter.py`
- [x] Pinecone settings in Settings → Integrations

## Phase 4: Conditional RAG orchestrator ✅

- [x] `conditional_rag_service.py` — multi-hop pipeline
- [x] Evidence bundles per hop
- [x] Tests: `test_conditional_rag_service.py`

## Phase 5: Evidence bundles ✅

- [x] `evidence_bundle_service.py` + `genai_evidence_bundles` table
- [x] Compliance Center export UI
- [x] RAG audit events
- [x] Tests: `test_evidence_bundle_service.py`, `test_rag_audit_service.py`

## Phase 6: IaC evidence ✅

- [x] Static Helm/OPA manifest scanner (`iac_evidence_service.py`)
- [x] Compliance Center IaC panel
- [x] Tests: `test_iac_evidence_service.py`

## Phase 7: Break-glass exemptions ✅

- [x] `policy_exemptions` table + `policy_exemption_service.py`
- [x] OPA exemption block + Rego `exemption_covers_movement`
- [x] Exemption CRUD API + Compliance Center panel
- [x] Governed RAG tester exemption ID field
- [x] Tests: `test_policy_exemption_service.py`

## Phase 8: Tenant config UI (Aug 15) ✅

- [x] IaC evidence tenant config — migration `059`, `iac_evidence_config_service.py`, configure modal
- [x] Data-movement policy tenant config — migration `060`, `data_movement_policy_service.py`, modal + OPA `tenant_policy`
- [x] Docker IaC fix — `./deploy:/deploy` mount; no `COPY deploy` in backend Dockerfile
- [x] Vault enabled by default in Compose (`VAULT_ENABLED=true`)
- [x] Tests: `test_data_movement_policy_service.py`

## Verification

```bash
cd backend && pytest tests/test_dlp_classification.py tests/test_opa_data_movement.py tests/test_evidence_bundle_service.py tests/test_conditional_rag_service.py tests/test_iac_evidence_service.py tests/test_data_movement_policy_service.py tests/test_rag_audit_service.py tests/test_seed_genai_dlp.py tests/test_policy_exemption_service.py -v
```

## Deferred (future)

- Full Checkov integration (static scanner v1 shipped)
- Weaviate / Qdrant adapters
- Approval workflow UI for exemptions
- Audit Explorer exemption event filter
