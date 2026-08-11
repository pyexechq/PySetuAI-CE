# ADR-001: Monorepo Structure

## Status

Accepted

## Context

PySetu AI requires a frontend (Next.js), backend (FastAPI), shared documentation, and deployment configuration. We need to decide between monorepo and polyrepo approaches.

## Decision

Use a monorepo with top-level directories: `frontend/`, `backend/`, `docs/`, and root-level `docker-compose.yml`.

## Alternatives Considered

1. **Polyrepo** — Separate repos for frontend and backend. Rejected due to coordination overhead for a small team and tightly coupled release cycles.
2. **Nx/Turborepo monorepo tool** — Rejected for Phase 1 simplicity; can adopt later if build orchestration complexity grows.

## Consequences

- Single clone gives full project context
- Docker Compose orchestrates all services from root
- Documentation lives alongside code
- Future: may add shared packages directory for types/contracts
