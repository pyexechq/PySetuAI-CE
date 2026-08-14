import uuid

import pytest

from app.services.rag_audit_service import write_rag_audit


class _FakeDb:
    def __init__(self) -> None:
        self.added = []

    def add(self, obj) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        return None


@pytest.mark.anyio
async def test_write_rag_audit_tags_module_metadata() -> None:
    db = _FakeDb()
    audit_id = await write_rag_audit(
        db,  # type: ignore[arg-type]
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        actor="admin@example.com",
        action="RAG Evaluate",
        resource="vector_store/upsert",
        status="blocked",
        risk="critical",
        details="test",
        usage_metadata={"sensitivity_labels": ["RESTRICTED_PII"]},
    )
    assert len(db.added) == 1
    log = db.added[0]
    assert log.id is not None
    assert log.action == "RAG Evaluate"
    assert log.usage_metadata["module"] == "rag_gateway"
    assert log.usage_metadata["sensitivity_labels"] == ["RESTRICTED_PII"]
