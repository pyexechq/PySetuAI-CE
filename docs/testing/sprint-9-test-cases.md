# Sprint 9 — Test Cases & Validation Matrix

**Milestone:** M8 — Universal AI Gateway Pipeline Parity  
**Status:** **100% Passed (152 Backend Unit Tests + Next.js UI Compilation Verified)**

---

## 1. S9-01: Routing Group Entity & CRUD API (BL-060)

| Test ID | Test Case | Target File / Module | Expected Result | Status |
|---------|-----------|----------------------|-----------------|--------|
| **TC-S9-01-01** | Verify `RoutingGroup` DB model instantiation & JSON schema for members/weights | `backend/tests/test_routing_groups.py` | `RoutingGroup` instantiates with strategy (`weighted`/`failover`), member list, and tenant scoping | **PASS** |
| **TC-S9-01-02** | Create routing group via CRUD API (`POST /v1/routing-groups`) | `backend/tests/test_routing_groups.py` | Returns HTTP 201 with created group details | **PASS** |
| **TC-S9-01-03** | Update routing group members and weights (`PUT /v1/routing-groups/{id}`) | `backend/tests/test_routing_groups.py` | Returns updated group object with modified strategy & weights | **PASS** |

---

## 2. S9-02: Group-as-Model Resolution (BL-060)

| Test ID | Test Case | Target File / Module | Expected Result | Status |
|---------|-----------|----------------------|-----------------|--------|
| **TC-S9-02-01** | Resolve request model `model: "production"` to routing group | `backend/tests/test_group_as_model_routing.py` | Gateway matches group alias name and selects member model | **PASS** |
| **TC-S9-02-02** | Weighted ratio selection across member models | `backend/tests/test_group_as_model_routing.py` | Model resolution probabilistically distributes according to weight ratios | **PASS** |
| **TC-S9-02-03** | Fallback to original model string if group is inactive | `backend/tests/test_group_as_model_routing.py` | Requests route safely without throwing errors | **PASS** |

---

## 3. S9-03: Gateway Auto-Failover & Failover Chain Audit Logging (BL-060)

| Test ID | Test Case | Target File / Module | Expected Result | Status |
|---------|-----------|----------------------|-----------------|--------|
| **TC-S9-03-01** | Auto-failover on upstream 5xx server error | `backend/tests/test_gateway_auto_failover.py` | Gateway catches 5xx error and retries next candidate in failover rank | **PASS** |
| **TC-S9-03-02** | Auto-failover on request timeout / HTTP connection failure | `backend/tests/test_gateway_auto_failover.py` | Gateway attempts failover model without failing client request | **PASS** |
| **TC-S9-03-03** | Audit log records complete failover chain | `backend/tests/test_gateway_auto_failover.py` | `AuditLog.details` records `failover_chain` list and final succeeded target model | **PASS** |

---

## 4. S9-04: LLM Router UI Routing Groups Tab & Modal (BL-060)

| Test ID | Test Case | Target File / Module | Expected Result | Status |
|---------|-----------|----------------------|-----------------|--------|
| **TC-S9-04-01** | Static build compilation of LLM Router UI | `frontend/src/components/llm-router/llm-router-view.tsx` | Next.js compilation completes with 0 TypeScript/ESLint errors | **PASS** |
| **TC-S9-04-02** | Routing group modal strategy toggle | `frontend/src/components/llm-router/routing-group-modal.tsx` | UI dynamically switches between Weighted Ratio (%) and Priority Failover Rank inputs | **PASS** |
| **TC-S9-04-03** | Member target addition & weight validation | `frontend/src/components/llm-router/routing-group-modal.tsx` | Member targets can be added/deleted and total weight is displayed | **PASS** |

---

## 5. S9-05: Regional Routing Spike (BL-077)

| Test ID | Test Case | Target File / Module | Expected Result | Status |
|---------|-----------|----------------------|-----------------|--------|
| **TC-S9-05-01** | AWS Bedrock regional endpoint resolution | `backend/tests/test_regional_adapters.py` | Resolves `ap-south-1`, `eu-central-1`, and `us-east-1` endpoints correctly | **PASS** |
| **TC-S9-05-02** | AWS Bedrock payload formatting | `backend/tests/test_regional_adapters.py` | Converts `ChatMessage` list to Anthropic Bedrock payload format | **PASS** |
| **TC-S9-05-03** | AWS Bedrock regional call execution | `backend/tests/test_regional_adapters.py` | Successfully executes regional invocation and returns response | **PASS** |
| **TC-S9-05-04** | GCP Vertex AI regional endpoint resolution | `backend/tests/test_regional_adapters.py` | Resolves `asia-south1`, `europe-west3`, and `us-central1` endpoints correctly | **PASS** |
| **TC-S9-05-05** | GCP Vertex AI payload formatting | `backend/tests/test_regional_adapters.py` | Converts `ChatMessage` list to Gemini Vertex AI payload format | **PASS** |
| **TC-S9-05-06** | GCP Vertex AI regional call execution | `backend/tests/test_regional_adapters.py` | Successfully executes regional invocation and returns response | **PASS** |

---

## 6. S9-06: Wire Alert Webhooks for Rate Limit & Token Budget Breaches (BL-075)

| Test ID | Test Case | Target File / Module | Expected Result | Status |
|---------|-----------|----------------------|-----------------|--------|
| **TC-S9-06-01** | Build alert event for rate limit & token budget breaches | `backend/tests/test_rate_limit_token_budget_alerts.py` | Constructs `gateway.rate_limit.block` and `gateway.token_budget.block` events | **PASS** |
| **TC-S9-06-02** | Webhook dispatch on AI rate limit breach (RPM/RPH/RPD) | `backend/tests/test_rate_limit_token_budget_alerts.py` | Gateway triggers `dispatch_tenant_alerts` on HTTP 429 rate limit block | **PASS** |
| **TC-S9-06-03** | Webhook dispatch on AI token budget breach (TPM/TPH/TPD) | `backend/tests/test_rate_limit_token_budget_alerts.py` | Gateway triggers `dispatch_tenant_alerts` on HTTP 429 token budget block | **PASS** |
