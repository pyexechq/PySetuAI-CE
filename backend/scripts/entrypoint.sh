#!/bin/sh
set -e

echo "Running database migrations..."
python -m alembic upgrade head

echo "Seeding demo data..."
python -m app.db.seed

echo "Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
