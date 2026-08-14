from uuid import uuid4

from app.services.gateway_context import GatewayContext
from app.services.opa_service import build_gateway_opa_input


def test_build_gateway_opa_input_includes_role_and_bundle() -> None:
    ctx = GatewayContext(
        tenant_id=uuid4(),
        actor="admin@acme.com",
        policy_bundle_name="Standard Support",
    )
    payload = build_gateway_opa_input(
        ctx,
        type("Req", (), {"model": "auto", "routing_context": None})(),
        routed_model="GPT-4o",
        has_pii=False,
        region="US",
        risk="low",
        content_length=2,
    )
    assert payload["subject"]["role"] == "client_key"
    assert payload["resource"]["bundle"] == "Standard Support"
    assert payload["request"]["routed_model"] == "GPT-4o"
    assert payload["environment"]["region"] == "US"
    assert payload["movement"]["to"] == "llm"
