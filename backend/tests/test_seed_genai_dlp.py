from app.db.seed_genai_dlp import _build_bundle_payload, _classification


def test_build_bundle_payload_conditional_rag_blocked() -> None:
    import uuid
    from datetime import UTC, datetime

    bundle_id = uuid.uuid4()
    audit_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    payload = _build_bundle_payload(
        bundle_id=bundle_id,
        actor="security@acme.com",
        tenant_id=tenant_id,
        audit_event_id=audit_id,
        bundle_type="conditional_rag",
        allowed=False,
        sensitivity="RESTRICTED_PII",
        destination="pinecone",
        blocked_hop="document_to_embedding",
        generated_at=datetime.now(UTC),
    )
    assert payload["pipeline"]["allowed"] is False
    assert payload["pipeline"]["blocked_hop"] == "document_to_embedding"
    assert payload["classification"]["highest_sensitivity"] == "RESTRICTED_PII"
    assert "HIPAA" in "".join(payload["control_mappings"])


def test_classification_maps_pii() -> None:
    result = _classification("RESTRICTED_PCI")
    assert "PCI Card" in result["entities"]
    assert result["highest_sensitivity"] == "RESTRICTED_PCI"
