import pytest

from app.services.conditional_rag_service import run_conditional_rag_pipeline
from app.services.embedding_service import embed_text
from app.services.evidence_bundle_service import build_rag_pipeline_evidence_bundle


class _Result:
    def __init__(self, value=None) -> None:
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return self._value or []


class _FakeDb:
    """Minimal async db double supporting the integration lookup used by the pipeline."""

    def __init__(self) -> None:
        self.added: list = []

    async def execute(self, _query):
        return _Result(None)

    def add(self, record) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        pass


@pytest.mark.anyio
async def test_embed_text_returns_mock_vector_without_api_key() -> None:
    result = await embed_text("Quarterly earnings summary", api_key=None, dimensions=8)
    assert result.source == "mock"
    assert len(result.vector) == 8


@pytest.mark.anyio
async def test_conditional_rag_blocks_restricted_pii_before_embedding(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.integration_service import GatewayConfig
    from app.services.pinecone_adapter import VectorStoreConfig

    async def _gateway_config(_db, _tenant_id):
        return GatewayConfig(
            openai_api_key=None,
            gemini_api_key=None,
            gemini_default_model="gemini-1.5-pro",
            ollama_enabled=False,
            ollama_base_url="http://localhost:11434",
            ollama_default_model="llama3.2",
            source="test",
        )

    async def _vector_config(_db, _tenant_id):
        return VectorStoreConfig(
            enabled=False,
            api_key=None,
            host=None,
            namespace="",
            dimension=8,
            source="test",
        )

    monkeypatch.setattr("app.services.conditional_rag_service.resolve_gateway_config", _gateway_config)
    monkeypatch.setattr("app.services.conditional_rag_service.resolve_vector_store_config", _vector_config)

    pipeline = await run_conditional_rag_pipeline(
        "SSN 123-45-6789 should not be indexed",
        db=_FakeDb(),  # type: ignore[arg-type]
        tenant_id="00000000-0000-0000-0000-000000000001",
    )
    assert pipeline.allowed is False
    assert pipeline.blocked_hop == "document_to_embedding"
    assert pipeline.hops[0].allowed is False


@pytest.mark.anyio
async def test_conditional_rag_allows_benign_content_without_pinecone(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.integration_service import GatewayConfig
    from app.services.pinecone_adapter import VectorStoreConfig

    async def _gateway_config(_db, _tenant_id):
        return GatewayConfig(
            openai_api_key=None,
            gemini_api_key=None,
            gemini_default_model="gemini-1.5-pro",
            ollama_enabled=False,
            ollama_base_url="http://localhost:11434",
            ollama_default_model="llama3.2",
            source="test",
        )

    async def _vector_config(_db, _tenant_id):
        return VectorStoreConfig(
            enabled=False,
            api_key=None,
            host=None,
            namespace="",
            dimension=8,
            source="test",
        )

    monkeypatch.setattr("app.services.conditional_rag_service.resolve_gateway_config", _gateway_config)
    monkeypatch.setattr("app.services.conditional_rag_service.resolve_vector_store_config", _vector_config)

    pipeline = await run_conditional_rag_pipeline(
        "Quarterly earnings summary for investors.",
        db=_FakeDb(),  # type: ignore[arg-type]
        tenant_id="00000000-0000-0000-0000-000000000001",
    )
    assert pipeline.hops[0].allowed is True
    assert pipeline.hops[1].allowed is True
    assert pipeline.embedding is not None
    assert pipeline.upsert is not None
    assert pipeline.upsert.mock is True


def test_build_rag_pipeline_evidence_bundle_includes_hops() -> None:
    from app.services.conditional_rag_service import ConditionalRagResult, RagPipelineHop
    from app.services.dlp_service import scan_content
    from app.services.pinecone_adapter import VectorUpsertResult

    dlp = scan_content("Quarterly earnings summary")
    pipeline = ConditionalRagResult(
        allowed=False,
        hops=[
            RagPipelineHop(
                hop="document_to_embedding",
                movement_from="document",
                movement_to="embedding",
                operation="embed",
                allowed=True,
            ),
            RagPipelineHop(
                hop="embedding_to_vector_store",
                movement_from="embedding",
                movement_to="pinecone",
                operation="upsert",
                allowed=False,
                blocked_locally=True,
            ),
        ],
        dlp=dlp,
        upsert=VectorUpsertResult(upserted=False, vector_id="doc-1", mock=True),
        blocked_hop="embedding_to_vector_store",
    )
    bundle = build_rag_pipeline_evidence_bundle(pipeline=pipeline, tenant_id="tenant-1", actor="auditor@example.com")
    assert bundle["bundle_type"] == "conditional_rag"
    assert len(bundle["pipeline"]["hops"]) == 2
    assert bundle["pipeline"]["blocked_hop"] == "embedding_to_vector_store"
