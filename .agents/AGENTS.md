# Agent Rules — PySetuAI Workspace

These rules apply to every AI coding agent working in this repository.
Read this file **before** running any Docker or database command.

---

## 🐳 Docker Builds — ALWAYS use `make`, never raw `docker compose --build`

This repository lives on a **macOS external volume** (`/Volumes/PyExec AI/…`).
macOS automatically creates hidden **AppleDouble sidecar files** (e.g. `._Dockerfile`,
`._*.py`) with extended attributes (`xattr`) that Docker BuildKit **cannot read**.
The error looks like:

```
failed to xattr /Volumes/PyExec AI/.../backend/._.pytest_deps: operation not permitted
```

### Required workflow

```bash
# ✅ Always use make — it runs dot_clean + find . -name "._*" -delete first
make build          # clean + rebuild ALL services
make build-backend  # clean + rebuild backend only
make build-frontend # clean + rebuild frontend only
make migrate        # docker compose exec backend alembic upgrade head
make ps             # show container status
make restart        # down + clean + rebuild all
make clean          # purge ._* / .DS_Store / __pycache__ without rebuilding
```

```bash
# ❌ Never do this — will fail with xattr errors on this machine
docker compose up -d --build
docker build ./backend
```

If you must run a raw Docker command for any reason, **always** run this first:

```bash
dot_clean . && find . -name "._*" -delete
```

---

## 🗃️ Alembic Migrations — revision ID constraints

### Rule 1 — revision IDs are VARCHAR(32) in the database

The `alembic_version` table stores `version_num` as `VARCHAR(32)`.
**Every `revision: str = "..."` value must be ≤ 32 characters.**

```python
# ✅ Good (20 chars)
revision: str = "040_bundles_intents"

# ❌ Bad — 34 chars, will fail with: value too long for type character varying(32)
revision: str = "040_policy_bundles_custom_intents"
```

### Rule 2 — revision IDs must form an unbroken chain

The `revision` string in a migration file **must exactly match** the
`down_revision` string referenced by the next migration.
A mismatch causes:

```
KeyError: '<revision_id>'
```

**Always verify the chain before adding a new migration:**

```bash
docker compose exec backend alembic history --verbose
```

### Rule 3 — check the live DB before diagnosing migration errors

```bash
docker compose exec postgres psql -U pysetu -d pysetu -c "SELECT * FROM alembic_version;"
```

If the DB contains a `version_num` that no longer matches any file's `revision`,
update the **file** to match the DB value (preserving history), or update the DB
to match the file — **never delete migration files**.

---

## 🏥 Container startup order

The `docker-compose.yml` dependency chain is:

```
postgres (healthy) ──┬──> backend (healthy) ──> frontend
vault    (healthy) ──┘                      └──> celery-beat (healthy)
redis    (started) ──────────────────────────> celery-worker (healthy)
```

If `frontend` or `celery-beat` are stuck in `Created`:

```bash
docker compose start frontend celery-beat
```

They were waiting for `backend` to become healthy first.

---

## 📋 Migration authoring checklist

When creating a new Alembic migration file:

- [ ] `revision` string ≤ 32 characters
- [ ] `down_revision` exactly matches the previous file's `revision` string
- [ ] File is named `NNN_short_description.py`
- [ ] Run `make build-backend && make migrate` (not raw docker commands)
- [ ] Verify with `docker compose exec postgres psql -U pysetu -d pysetu -c "SELECT * FROM alembic_version;"`

---

## 🔑 Key service URLs (local dev)

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8001 |
| API Docs (Swagger) | http://localhost:8001/docs |
| Mailhog (email) | http://localhost:8025 |
| Vault UI | http://localhost:8200 (enabled by default; token `dev-root-token`) |
| OPA | http://localhost:8181 |

Default login: `admin@acme.com` / `demo1234` (tenant: `acme`)

---

## 📁 Key files

| File | Purpose |
|------|---------|
| `Makefile` | **Use this for all Docker operations** |
| `docker-compose.yml` | Service definitions |
| `backend/.dockerignore` | Excludes `._*`, `__pycache__`, `.venv` from build context |
| `backend/alembic/versions/` | Migration files — revision IDs must be ≤ 32 chars |
| `.env.docker` | Environment overrides for local Docker dev |
| `docs/planning/product-roadmap.md` | Current phase & milestone status |
| `docs/planning/current-sprint.md` | Active sprint tasks |
