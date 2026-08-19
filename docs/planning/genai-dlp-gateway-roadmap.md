# GenAI DLP Gateway — Product Roadmap

> **Vision:** PySetu becomes an enterprise GenAI DLP gateway — governing prompts, embeddings, and vector-store writes with OPA-backed data-movement policy, DLP classification, and auditor-ready evidence bundles.

## Current foundation

| Capability | Status | Location |
|------------|--------|----------|
| Regex PII/PHI/PCI detection | ✅ Shipped | `backend/app/services/dlp_service.py` |
| Gateway ingress DLP + redaction | ✅ Shipped | `backend/app/services/gateway_service.py` |
| OPA ABAC (bundle, role, risk) | ✅ Shipped | `deploy/opa/policies/gateway.rego` |
| Audit trail (LLM + MCP) | ✅ Shipped | Gateway + MCP audit services |
| Vector DB / RAG governance | ✅ Shipped | `rag_gateway` API + conditional RAG pipeline |
| Evidence bundles for auditors | ✅ Shipped | `genai_evidence_bundles` + Compliance Center export |

## Phased delivery

### Phase 1 — DLP v2 (sensitivity labels) — **Done**

Map detector entities to enterprise sensitivity tiers:

| Detector label | Sensitivity label |
|----------------|-------------------|
| SSN, US Phone, EU Personal ID | `RESTRICTED_PII` |
| Email | `INTERNAL_PII` |
| PHI | `RESTRICTED_PHI` |
| PCI Card | `RESTRICTED_PCI` |
| Financial Account | `CONFIDENTIAL_FINANCIAL` |

**Deliverables:** `dlp_classification.py`, extended `DlpScanResult` / scan API response, gateway audit detail includes sensitivity.

### Phase 2 — OPA data-movement schema — **Done**

Extend OPA input with:

```json
{
  "data": {
    "classifications": ["SSN", "Email"],
    "sensitivity_labels": ["RESTRICTED_PII", "INTERNAL_PII"],
    "highest_sensitivity": "RESTRICTED_PII"
  },
  "movement": {
    "from": "prompt",
    "to": "llm",
    "operation": "completion"
  }
}
```

**Rego rules:** Block `RESTRICTED_PII`, `RESTRICTED_PHI`, `RESTRICTED_PCI` → `pinecone` / `vector_store` / `embedding`.

### Phase 3 — RAG Gateway (Pinecone adapter) — **Done**

Governed HTTP API for embed / upsert / query against configured vector stores. Every hop: DLP → OPA movement → audit → (optional) provider call.

**Delivered:** `embedding_service.py`, `pinecone_adapter.py`, `POST /rag-gateway/ingest`, governed upsert with real Pinecone when configured.

### Phase 4 — Conditional RAG orchestrator — **Done (v1)**

Pipeline: ingest document → classify → OPA per hop (document→embedding, embedding→vector_store) → embed only if allowed → upsert only if allowed.

**Delivered:** `conditional_rag_service.py`, multi-hop evidence bundles.

### Phase 5 — Evidence bundle service — **Done**

Immutable JSON bundles persisted to `genai_evidence_bundles`; export via API and Compliance Center UI panel. RAG operations write linked audit events.

### Phase 6 — IaC evidence (Checkov / Terraform) — **Done (static scanner v1)**

Static Helm/OPA manifest scanner with control mappings; export from Compliance Center. **Tenant config UI** (scan paths + checks) shipped Aug 15 (BL-117). Deploy root via `IAC_DEPLOY_ROOT` + `./deploy` volume in Docker Compose. Full Checkov integration deferred.

### Phase 7 — Break-glass exemptions — **Done**

See **Break-glass exemptions** section below.

### Phase 8 — Tenant policy configuration UI — **Done (Aug 15)**

| Capability | UI | API |
|------------|-----|-----|
| OPA data-movement rules (labels → destinations) | Compliance → GenAI DLP → **Data-movement policy** | `GET/PUT/POST /compliance/data-movement-policy` |
| IaC scanner paths & checks | Compliance → Infrastructure evidence → **Configure** | `GET/PUT/POST /compliance/iac-evidence/config` |

**Not in Policy Studio:** ingress regex rules (Block/Redact) vs vector data-movement (OPA) are separate surfaces.

## Demo data

On startup in `debug` mode, `seed_genai_dlp_demo_events()` inserts **6 demo scenarios** per tenant (if none exist):

| Scenario | Result |
|----------|--------|
| Product FAQ ingest | Allowed → Pinecone |
| SSN in document | Blocked at `document_to_embedding` |
| PHI patient record | Blocked before vector store |
| Investor summary evaluate | Allowed dry-run |
| PCI card upsert | Blocked |
| Help-center article upsert | Allowed (mock index) |

Also seeds demo Pinecone host on tenant integrations.

**Manual reload (debug only):** `POST /api/v1/rag-gateway/demo-events` or **Compliance Center → Load demo RAG events**.

## Break-glass exemptions (shipped)

Time-bound overrides for **embedding** and **llm** hops only (`POST /rag-gateway/exemptions`). Pass `exemption_id` on evaluate/upsert/ingest requests.

| Rule | Behavior |
|------|----------|
| PHI / PCI | Never exemptable to any vector hop |
| RESTRICTED_PII | Exemptable to `embedding` only, not Pinecone/vector upsert |
| Audit | `Policy Exemption Created/Applied/Revoked` + evidence metadata |

- **Block rate:** Restricted labels never reach vector stores (OPA + integration tests).
- **Audit completeness:** Every governed RAG operation has classification + OPA + movement in audit.
- **Time-to-evidence:** Auditor can export a bundle for a blocked upsert in &lt; 1 click (Phase 5).

## Related docs

- [Implementation plan](../superpowers/plans/2026-08-14-genai-dlp-gateway.md)
- [Gateway parity roadmap](./gateway-parity-roadmap.md)
- [Future enhancements](./future-enhancements.md) — RAG source governance

## Backlog IDs

| ID | Item | Phase |
|----|------|-------|
| BL-109 | DLP sensitivity label mapping | 1 |
| BL-110 | OPA data-movement Rego rules | 2 |
| BL-111 | RAG gateway API (stub → Pinecone) | 3 |
| BL-112 | Conditional RAG orchestrator | 4 |
| BL-113 | GenAI evidence bundle export | 5 |
| BL-114 | IaC evidence (Checkov) | 6 |
| BL-115 | Break-glass policy exemptions | 7 |
| BL-117 | Tenant IaC scanner config UI + API | 8 |
| BL-118 | Tenant data-movement policy UI + API | 8 |

> Aug 15 UX batch (BL-116–BL-122): [aug-15-compliance-ux-update.md](../progress/aug-15-compliance-ux-update.md)
