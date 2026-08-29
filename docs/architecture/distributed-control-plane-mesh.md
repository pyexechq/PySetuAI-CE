# Distributed Control Plane & Regional Edge Gateway Mesh

## 1. Executive Summary

Modern enterprise AI deployments require **sub-millisecond local execution latency**, strict **regional data sovereignty (GDPR / HIPAA)**, and **centralized policy governance**.

To satisfy these requirements, PySetu AI decouples into two specialized tiers:
1. **Central Control Plane (Global Management Hub)**: Centralized management of tenants, user authentication, Policy Studio (OPA Rego authoring), Vault cryptographic key custody, compliance evidence generation, and billing.
2. **Regional Edge AI Gateways (Stateless Data Plane)**: Lightweight, stateless gateway instances deployed in edge cloud regions (e.g. AWS `us-east-1`, `eu-central-1`, `ap-northeast-1`) or customer private on-premises Kubernetes clusters.

---

## 2. Global Architecture & Mesh Topology

```
                                  ┌──────────────────────────────────────────────────────────┐
                                  │            CENTRAL CONTROL PLANE (Global Hub)            │
                                  │   (Tenant Mgmt • Policy Studio • Vault Key Custody •     │
                                  │    Compliance Bundles • Developer Portal • Analytics)    │
                                  └─────────────────────────────┬────────────────────────────┘
                                                                │
                                   Push Policy Bundles & Keys   │   Async Batch Audit & Metrics
                                   (HTTPS / OPA Bundle Sync)    │   (Zero Latency Impact)
                                                                │
                 ┌──────────────────────────────────────────────┼──────────────────────────────────────────────┐
                 ▼                                              ▼                                              ▼
  ┌──────────────────────────────┐               ┌──────────────────────────────┐               ┌──────────────────────────────┐
  │   REGIONAL GATEWAY (EDGE)    │               │   REGIONAL GATEWAY (EDGE)    │               │  ON-PREM / CUSTOMER VPC EDGE │
  │        [ US-East (N. VA) ]   │               │       [ Europe (Frankfurt) ] │               │      [ Private K8s Cluster ] │
  ├──────────────────────────────┤               ├──────────────────────────────┤               ├──────────────────────────────┤
  │ • Local UAG Reverse Proxy    │               │ • Local UAG Reverse Proxy    │               │ • Local UAG Reverse Proxy    │
  │ • Local OPA Bundle (<0.5ms)  │               │ • Local OPA Bundle (GDPR)    │               │ • Local OPA Bundle           │
  │ • In-Flight Stream DLP       │               │ • In-Flight Stream DLP       │               │ • Local DLP (No data leaves) │
  │ • Local Rate Limiting Cache  │               │ • Local Rate Limiting Cache  │               │ • Local Rate Limiting Cache  │
  └──────────────┬───────────────┘               └──────────────┬───────────────┘               └──────────────┬───────────────┘
                 │                                              │                                              │
                 ▼                                              ▼                                              ▼
        [ OpenAI / Bedrock US ]                        [ Azure OpenAI Europe ]                     [ Local vLLM / Ollama ]
```

---

## 3. Data Plane Execution Pipeline (Sub-2ms Overhead)

When a client application or developer IDE makes a request to a Regional Edge Gateway:
1. **Zero Central Database Queries:** The edge gateway validates client API key hashes against its local in-memory key table.
2. **In-Flight Stream DLP (<1.5ms):** Regex and NER entities are classified and masked in streaming memory chunks.
3. **Local OPA Policy Evaluation (<0.5ms):** Declarative Rego policies evaluate tenant rules against the request.
4. **Direct Regional Model Dispatch:** The edge gateway dispatches the sanitized request directly to the nearest regional LLM endpoint (e.g. AWS Bedrock Frankfurt).
5. **Asynchronous Telemetry Ingestion:** The edge gateway buffers audit hashes and token counters, flushing them in background batches to the Central Control Plane (`POST /api/v1/edge/telemetry/batch`).

---

## 4. Policy & Key Bundle Synchronization (`/api/v1/edge/bundle`)

The Central Control Plane compiles tenant configurations into a signed **Edge Sync Bundle**:
* **Hashed Client API Keys:** Key hashes, rate limit quotas, and tenant bindings.
* **Compiled OPA Rego Policies:** Data movement rules, role mappings, and break-glass overrides.
* **Model Aliases:** Routing provider mappings (`gpt-4o` $\to$ `openai/gpt-4o`).
* **DLP Entity Dictionaries:** Regex patterns and entity masking tags.

### Downlink Protocol:
* Edge nodes poll `/api/v1/edge/bundle?region={region}` during initialization and on heartbeat update signals.
* Updates apply dynamically in memory without restarting the gateway container.

---

## 5. Offline Survivability & Fault Tolerance

If the Central Control Plane undergoes maintenance, experiences network partitions, or is temporarily unreachable:
* **Zero Disruption to AI Workloads:** Regional Edge Gateways continue processing requests using their locally cached OPA policy bundle and validated key tables.
* **Local Audit Buffering:** Telemetry and audit events are stored in a local ring buffer (or local Redis) and retransmitted automatically once connection to the Central Hub is restored.

---

## 6. Quick-Start Deployment Guide

### Deploying a Regional Edge Gateway via Docker:
```bash
docker run -d \
  --name pysetu-edge-gateway \
  -p 8001:8001 \
  -e APP_MODE=edge_gateway \
  -e CONTROL_PLANE_URL=https://pysetu.io \
  -e EDGE_NODE_TOKEN=pysetu_edge_YOUR_ENROLLMENT_TOKEN \
  -e EDGE_REGION=eu-central-1 \
  pysetu/gateway:latest
```

### Kubernetes Helm Values Example:
```yaml
appMode: edge_gateway
controlPlane:
  url: "https://pysetu.io"
  enrollmentSecretName: "pysetu-edge-token"
region: "eu-central-1"
replicaCount: 3
autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70
```
