from app.services.policy_exemption_service import (
    ExemptionContext,
    exemption_allows_movement,
    exemption_blocks_local_override,
)


def test_exemption_blocks_phi_to_embedding() -> None:
    assert exemption_blocks_local_override(["RESTRICTED_PHI"], "embedding") is True


def test_exemption_allows_restricted_pii_to_embedding_with_context() -> None:
    context = ExemptionContext(
        id="ex-1",
        reason="Legal review ticket INC-99",
        ticket_ref="INC-99",
        allowed_destinations=["embedding", "llm"],
        expires_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )
    result = exemption_allows_movement(context, destination="embedding", sensitivity_labels=["RESTRICTED_PII"])
    assert result.valid is True


def test_exemption_denies_restricted_pii_to_vector_store() -> None:
    context = ExemptionContext(
        id="ex-2",
        reason="Should not allow vector upsert",
        ticket_ref=None,
        allowed_destinations=["embedding", "llm"],
        expires_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
    )
    result = exemption_allows_movement(
        context,
        destination="vector_store",
        sensitivity_labels=["RESTRICTED_PII"],
    )
    assert result.valid is False
