import pytest

from app.services.data_movement_service import evaluate_content_movement
from app.services.evidence_bundle_service import build_evidence_bundle


@pytest.mark.anyio
async def test_build_evidence_bundle_includes_classification_and_controls() -> None:
    movement = await evaluate_content_movement(
        "Patient diagnosis: asthma",
        destination="pinecone",
        operation="upsert",
        tenant_id="tenant-abc",
    )
    bundle = build_evidence_bundle(
        movement_result=movement,
        tenant_id="tenant-abc",
        actor="auditor@example.com",
    )
    assert bundle["id"]
    assert bundle["classification"]["highest_sensitivity"] == "RESTRICTED_PHI"
    assert bundle["movement"]["to"] == "pinecone"
    assert bundle["policy"]["allowed"] is False
    assert "HIPAA §164.502" in bundle["control_mappings"]
