# DevOps Agent Handoff

**Last Updated:** Aug 15, 2026

## Work Completed

- Created Docker Compose stack with postgres, redis, vault, opa, backend, frontend, celery worker/beat
- Kubernetes Helm chart at `deploy/helm/pysetu` (S4-35 / BL-031)
- Air-gap offline bundle at `deploy/airgap` (S4-36 / BL-032)
- Backend Dockerfile (Python 3.12-slim)
- Frontend Dockerfile (Node 20-alpine, multi-stage build)
- Environment variable configuration for database, Redis, JWT, OPA

## Aug 15 updates

| Change | Detail |
|--------|--------|
| **Vault default-on** | `VAULT_ENABLED=true` in Compose + `.env.docker`; backend `vault_enabled=True` |
| **IaC deploy mount** | `./deploy:/deploy:ro`, `IAC_DEPLOY_ROOT=/deploy`; removed invalid `COPY deploy` from Dockerfile |
| **Migrations** | `059_iac_evidence_tenant_config`, `060_data_movement_policy` — run `make migrate` after pull |
| **Helm** | `values.yaml` `vaultEnabled: "true"`; air-gap/minikube profiles keep Vault off |
| **Docs** | [vault-deployment.md](../security/vault-deployment.md), [aug-15-compliance-ux-update.md](../progress/aug-15-compliance-ux-update.md) |

## Files Modified

```
docker-compose.yml
.env.docker
backend/Dockerfile
backend/app/config.py
deploy/helm/pysetu/values.yaml
deploy/helm/pysetu/values-minikube.yaml
```

## Design Decisions

- PostgreSQL 16 Alpine for database
- Redis 7 Alpine for cache/queue
- Named volume for postgres persistence
- Backend exposed on host port **8001** (default), frontend on 3000
- Vault dev server on 8200 with root token `dev-root-token` (Compose only)

## Risks

- Air-gap bundles intentionally disable Vault (`VAULT_ENABLED=false`)
- Local uvicorn without Docker needs Vault on :8200 or `VAULT_ENABLED=false`
