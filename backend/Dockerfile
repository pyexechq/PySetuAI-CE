FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY tests ./tests
COPY alembic ./alembic
COPY alembic.ini .
COPY pytest.ini .

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "python -m alembic upgrade head && python -m app.db.seed && python -m app.db.seed_governance && python -c \"import asyncio; from app.db.seed_data_protection import seed_data_protection_residency_samples; asyncio.run(seed_data_protection_residency_samples())\" && python -c \"import asyncio; from app.db.seed_blog import seed_blog_articles; asyncio.run(seed_blog_articles())\" && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
