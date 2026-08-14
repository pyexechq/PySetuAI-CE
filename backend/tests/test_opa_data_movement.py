import pytest

from app.services.data_movement_service import evaluate_content_movement
from app.services.opa_service import build_data_movement_opa_input, build_gateway_opa_input
from app.services.gateway_context import GatewayContext
from uuid import uuid4


def test_build_data_movement_opa_input_includes_movement_and_data() -> None:
    payload = build_data_movement_opa_input(
        tenant_id="tenant-1",
        bundle_name="Strict Security",
        region="EU",
        risk="high",
        entity_classifications=["SSN"],
        sensitivity_labels=["RESTRICTED_PII"],
        highest_sensitivity_label="RESTRICTED_PII",
        movement_from="document",
        movement_to="vector_store",
        movement_operation="upsert",
    )
    assert payload["movement"]["to"] == "vector_store"
    assert payload["data"]["highest_sensitivity"] == "RESTRICTED_PII"


def test_build_gateway_opa_input_includes_sensitivity() -> None:
    ctx = GatewayContext(
        tenant_id=uuid4(),
        actor="admin@acme.com",
        policy_bundle_name="Standard Support",
    )
    payload = build_gateway_opa_input(
        ctx,
        type("Req", (), {"model": "auto", "routing_context": None})(),
        routed_model="GPT-4o",
        has_pii=True,
        region="US",
        risk="medium",
        content_length=42,
        entity_classifications=["SSN"],
        sensitivity_labels=["RESTRICTED_PII"],
        highest_sensitivity="RESTRICTED_PII",
    )
    assert payload["data"]["sensitivity_labels"] == ["RESTRICTED_PII"]
    assert payload["movement"]["to"] == "llm"


@pytest.mark.anyio
async def test_evaluate_content_movement_blocks_restricted_pii_to_vector_store() -> None:
    result = await evaluate_content_movement(
        "SSN 123-45-6789 for indexing",
        destination="vector_store",
        operation="upsert",
    )
    assert result.allowed is False
    assert result.blocked_locally is True
    assert "RESTRICTED_PII" in result.dlp.sensitivity_labels


@pytest.mark.anyio
async def test_evaluate_content_movement_allows_benign_content_to_vector_store() -> None:
    result = await evaluate_content_movement(
        "Quarterly earnings summary for investors.",
        destination="vector_store",
        operation="upsert",
    )
    assert result.allowed is True
    assert result.blocked_locally is False
