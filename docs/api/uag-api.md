# UAG API

**Base path:** `/api/v1/uag`  
**Auth:** JWT with role `tenant_admin`, `security_admin`, or `platform_admin`

## Endpoints

### Model mappings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/mappings` | List tenant model mappings |
| POST | `/mappings` | Create mapping |
| PUT | `/mappings/{id}` | Update mapping |
| DELETE | `/mappings/{id}` | Delete mapping |

**Create body:**

```json
{
  "requested_model": "gpt-4o",
  "actual_model": "gemini-1.5-pro",
  "target_provider": "gemini",
  "emulate_protocol": "openai"
}
```

### Translation policies

| Method | Path | Description |
|--------|------|-------------|
| GET | `/policies` | List provider translation policies |
| POST | `/policies` | Create policy |
| PUT | `/policies/{id}` | Update policy (including enable/disable) |
| DELETE | `/policies/{id}` | Delete policy |

**Create body:**

```json
{
  "name": "Finance to local LLM",
  "conditions": { "department": "finance" },
  "actions": { "route_to": "ollama" },
  "priority": 10
}
```

### Statistics

| Method | Path | Description |
|--------|------|-------------|
| GET | `/stats` | Translation totals, success rate, latency, compatibility scores |

### Simulator

| Method | Path | Description |
|--------|------|-------------|
| POST | `/simulate` | Preview OpenAI request → canonical → translated upstream payload |

**Simulate body:**

```json
{
  "model": "gpt-4o",
  "messages": [{ "role": "user", "content": "Summarize risk posture." }],
  "routing_context": { "department": "finance" }
}
```

## Gateway integration

Live chat completions run UAG in `gateway_service.prepare_chat_request()` before DLP/policy and `run_uag_post_upstream()` after upstream response. Audit logs append `|uag_trace={...}` when translation occurs.
