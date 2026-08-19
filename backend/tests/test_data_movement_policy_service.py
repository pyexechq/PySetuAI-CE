from app.services.data_movement_policy_service import (
    DEFAULT_DATA_MOVEMENT_POLICY,
    policy_blocks_movement,
    resolve_data_movement_policy,
)


def test_resolve_data_movement_policy_defaults() -> None:
    policy, customized = resolve_data_movement_policy(None)
    assert customized is False
    assert policy == DEFAULT_DATA_MOVEMENT_POLICY


def test_policy_blocks_restricted_pii_to_vector_store() -> None:
    assert policy_blocks_movement(
        DEFAULT_DATA_MOVEMENT_POLICY,
        sensitivity_labels=["RESTRICTED_PII"],
        destination="vector_store",
    )


def test_policy_allows_public_to_vector_store() -> None:
    assert not policy_blocks_movement(
        DEFAULT_DATA_MOVEMENT_POLICY,
        sensitivity_labels=["PUBLIC"],
        destination="vector_store",
    )
