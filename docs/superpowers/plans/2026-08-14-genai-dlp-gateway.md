# GenAI DLP Gateway — Implementation Plan

> **For agent:** Execute Phase 1–2 in this session; Phases 3–6 are follow-up work.

**Goal:** Extend PySetu from LLM ingress DLP to a governed data-movement control plane with sensitivity labels, OPA enforcement for vector destinations, RAG gateway stub, and evidence bundles.

**Architecture:** DLP scan → sensitivity mapping → OPA input (`data` + `movement`) → allow/deny → audit + evidence JSON.

**Tech stack:** Python/FastAPI, OPA/Rego, existing `dlp_service` + `opa_service` + `gateway_service`.

---

## Phase 1: DLP v2 — Sensitivity labels

### Task 1.1: Classification mapper

**Files:**
- Create: `backend/app/services/dlp_classification.py`
- Modify: `backend/app/services/dlp_service.py`
- Test: `backend/tests/test_dlp_classification.py`

- [ ] **Step 1:** Add `ENTITY_TO_SENSITIVITY`, `derive_sensitivity_labels()`, `highest_sensitivity()`.
- [ ] **Step 2:** Extend `DlpScanResult` with `sensitivity_labels`, `highest_sensitivity`.
- [ ] **Step 3:** Call mapper from `scan_content()`.
- [ ] **Step 4:** Run `pytest backend/tests/test_dlp_classification.py -v`.

### Task 1.2: API + schemas

**Files:**
- Modify: `backend/app/schemas/data_protection.py`
- Modify: `backend/app/api/v1/data_protection.py`
- Modify: `backend/tests/test_data_protection_service.py`

- [ ] **Step 1:** Add fields to `DlpScanResponse`.
- [ ] **Step 2:** Return new fields from scan endpoint.
- [ ] **Step 3:** Update existing scan tests.

---

## Phase 2: OPA data-movement

### Task 2.1: OPA input extension

**Files:**
- Modify: `backend/app/services/opa_service.py`
- Modify: `backend/tests/test_opa_service.py`

- [ ] **Step 1:** Add `data` and `movement` blocks to `build_gateway_opa_input()`.
- [ ] **Step 2:** Pass `sensitivity_labels` / `entity_classifications` from `evaluate_gateway_abac()`.
- [ ] **Step 3:** Add `build_data_movement_opa_input()` for RAG paths.

### Task 2.2: Rego rules

**Files:**
- Modify: `deploy/opa/policies/gateway.rego`
- Modify: `deploy/helm/pysetu/files/gateway.rego`

- [ ] **Step 1:** Add `restricted_data_movement` set and vector destination rules.
- [ ] **Step 2:** Block restricted labels → `pinecone`, `vector_store`, `embedding`.

### Task 2.3: Gateway wiring

**Files:**
- Modify: `backend/app/services/gateway_service.py`

- [ ] **Step 1:** Pass DLP sensitivity into `evaluate_gateway_abac()`.
- [ ] **Step 2:** Include sensitivity in DLP audit detail.

### Task 2.4: Data movement service

**Files:**
- Create: `backend/app/services/data_movement_service.py`
- Test: `backend/tests/test_opa_data_movement.py`

- [ ] **Step 1:** `evaluate_content_movement(content, destination, operation)` → DLP + OPA.
- [ ] **Step 2:** Unit tests for blocked PII → vector_store.

---

## Phase 3: RAG gateway stub (this session — minimal)

### Task 3.1: API

**Files:**
- Create: `backend/app/schemas/rag_gateway.py`
- Create: `backend/app/api/v1/rag_gateway.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1:** `POST /rag-gateway/evaluate` — dry-run movement check.
- [ ] **Step 2:** `POST /rag-gateway/upsert` — governed stub (no Pinecone yet); returns allow/deny + evidence id.

---

## Phase 4: Evidence bundles (this session — minimal)

### Task 4.1: Evidence service

**Files:**
- Create: `backend/app/services/evidence_bundle_service.py`
- Test: `backend/tests/test_evidence_bundle_service.py`

- [ ] **Step 1:** `build_evidence_bundle()` — JSON with classification, movement, OPA, control refs.
- [ ] **Step 2:** Wire into RAG gateway responses.

---

## Verification

```bash
cd backend && pytest tests/test_dlp_classification.py tests/test_opa_data_movement.py tests/test_evidence_bundle_service.py tests/test_opa_service.py tests/test_data_protection_service.py -v
```

---

## Out of scope (later sessions)

- Real Pinecone / Weaviate adapters
- Conditional RAG document pipeline
- Compliance Center UI for evidence export
- Checkov / Terraform scanner
