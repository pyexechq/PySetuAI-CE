# Regional Routing Spike Architecture — AWS Bedrock & GCP Vertex AI Adapters

## Overview & Purpose

As part of **BL-077 (Regional Routing Spike)** in Phase 7 / Sprint 9, this architectural specification outlines the design pattern and adapter interfaces for multi-cloud regional LLM request routing in PySetu AI.

Enterprise compliance frameworks (e.g. GDPR, DPDP India, HIPAA) require strict data residency guarantees. PySetu AI's Gateway dynamically routes requests to cloud providers in compliance-approved geographic regions (e.g. `us-east-1`, `eu-central-1`, `ap-south-1`) based on tenant region policies and latency benchmarks.

---

## Architecture Diagram

```
                              ┌───────────────────────────────────┐
                              │     PySetu AI Gateway API         │
                              └─────────────────┬─────────────────┘
                                                │
                                    Regional Routing Engine
                                                │
                     ┌──────────────────────────┼──────────────────────────┐
                     ▼                          ▼                          ▼
         ┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
         │  AWS Bedrock Adapter  │  │ GCP Vertex AI Adapter │  │ Azure OpenAI Adapter  │
         └───────────┬───────────┘  └───────────┬───────────┘  └───────────┬───────────┘
                     │                          │                          │
         ┌───────────┴───────────┐  ┌───────────┴───────────┐  ┌───────────┴───────────┐
         │ us-east-1 / ap-south-1│  │us-central1/asia-south1│  │  eastus / switzerland │
         └───────────────────────┘  └───────────────────────┘  └───────────────────────┘
```

---

## Provider Adapter Specifications

### 1. AWS Bedrock Adapter (`backend/app/services/regional_adapters/bedrock_adapter.py`)
- **Supported Regions**: `us-east-1` (US East N. Virginia), `eu-central-1` (Europe Frankfurt), `ap-south-1` (India Mumbai).
- **Supported Model Inferences**:
  - `anthropic.claude-3-5-sonnet-20241022-v2:0`
  - `amazon.titan-text-express-v1`
  - `meta.llama3-70b-instruct-v1:0`
- **Authentication**: AWS SigV4 / IAM Role Credentials (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`).
- **Endpoint Structure**: `https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke`

### 2. GCP Vertex AI Adapter (`backend/app/services/regional_adapters/vertex_adapter.py`)
- **Supported Regions**: `us-central1` (Iowa), `europe-west3` (Frankfurt), `asia-south1` (Mumbai).
- **Supported Model Inferences**:
  - `gemini-1.5-pro`
  - `gemini-1.5-flash`
- **Authentication**: Google Application Default Credentials (ADC) / Bearer token via Service Account.
- **Endpoint Structure**: `https://{region}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{region}/publishers/google/models/{model_id}:generateContent`

---

## Canonical Request & Response Translation

To enforce Universal AI Gateway (UAG) parity across OpenAI, Gemini, Bedrock, and Vertex:

1. **Ingress Canonicalization**:
   Incoming OpenAI-compatible request body (`/v1/chat/completions`) is translated to standard `ChatMessage(role, content)` lists.

2. **Regional Adapter Dispatch**:
   The adapter maps `ChatMessage` to provider-specific payloads:
   - **Bedrock (Claude)**: `{ "anthropic_version": "bedrock-2023-05-31", "messages": [...], "max_tokens": 1000 }`
   - **Vertex AI (Gemini)**: `{ "contents": [{ "role": "user", "parts": [{ "text": ... }] }] }`

3. **Egress Normalization**:
   The response is translated back into standard `ChatCompletionResponse` format with usage token counts and `pysetu` metadata detailing region and provider latency.
