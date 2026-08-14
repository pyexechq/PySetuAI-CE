from app.services.uag_migration_helpers import (
    merge_aliases,
    uag_conditions_to_routing_condition,
    uag_policy_to_routing_fields,
)


def test_uag_conditions_to_routing_condition() -> None:
    assert uag_conditions_to_routing_condition({"department": "finance"}) == 'department == "finance"'
    assert uag_conditions_to_routing_condition({}) == "default"


def test_uag_policy_to_routing_fields_provider() -> None:
    model, provider, response_format = uag_policy_to_routing_fields({"route_to": "ollama"})
    assert provider == "ollama"
    assert model == "llama3.2"
    assert response_format == "auto"


def test_uag_policy_to_routing_fields_emulate_only() -> None:
    model, provider, response_format = uag_policy_to_routing_fields({"emulate": "openai"})
    assert provider is None
    assert model == "gpt-4o"
    assert response_format == "openai"


def test_merge_aliases_deduplicates() -> None:
    assert merge_aliases(["gpt-4"], "gpt-4", "GPT-4") == ["gpt-4"]
