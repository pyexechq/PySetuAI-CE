"""Text embedding for governed RAG pipelines."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass
class EmbeddingResult:
    vector: list[float]
    model: str
    source: str
    dimensions: int


def _mock_embedding(text: str, *, dimensions: int) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    seed = int.from_bytes(digest[:8], "big")
    for index in range(dimensions):
        seed = (seed * 1103515245 + 12345 + index) & 0x7FFFFFFF
        values.append((seed % 1000) / 1000.0)
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


async def embed_text(
    text: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    dimensions: int = 1536,
) -> EmbeddingResult:
    embedding_model = model or settings.embedding_model
    key = api_key or settings.openai_api_key
    if not key:
        return EmbeddingResult(
            vector=_mock_embedding(text, dimensions=dimensions),
            model=f"{embedding_model}-mock",
            source="mock",
            dimensions=dimensions,
        )

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"input": text, "model": embedding_model},
        )
        response.raise_for_status()
        body = response.json()

    vector = body["data"][0]["embedding"]
    return EmbeddingResult(
        vector=vector,
        model=embedding_model,
        source="openai",
        dimensions=len(vector),
    )
