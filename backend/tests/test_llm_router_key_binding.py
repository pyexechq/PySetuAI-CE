"""Routing rules with assigned client API keys."""

import asyncio
import uuid

from app.models.governance import RoutingRule
from app.services.llm_router import RoutingDecision, select_model


class _Scalars:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def all(self) -> list:
        return self._rows


class _ExecuteResult:
    def __init__(self, rows: list) -> None:
        self._rows = rows

    def all(self) -> list:
        return self._rows

    def scalars(self) -> _Scalars:
        return _Scalars(self._rows)


class _FakeDb:
    def __init__(self, results: list) -> None:
        self._results = results
        self._index = 0

    async def execute(self, _query):
        result = self._results[self._index]
        self._index += 1
        return result


def test_key_scoped_rule_only_matches_assigned_key() -> None:
    tenant_id = uuid.uuid4()
    rule_id = uuid.uuid4()
    key_a = uuid.uuid4()
    key_b = uuid.uuid4()

    rule = RoutingRule(
        id=rule_id,
        tenant_id=tenant_id,
        name="key-only",
        priority=1,
        condition="task.type == 'billing'",
        target_model="billing-model",
        status="active",
    )

    async def run(client_key_id: uuid.UUID | None) -> RoutingDecision:
        db = _FakeDb(
            [
                _ExecuteResult([(rule_id, key_a)]),
                _ExecuteResult([]),
                _ExecuteResult([]),
                _ExecuteResult([rule]),
            ]
        )
        return await select_model(
            "auto",
            db,
            tenant_id,
            {"task": {"type": "billing"}},
            client_api_key_id=client_key_id,
        )

    decision = asyncio.run(run(key_a))
    assert decision.model == "billing-model"
    assert decision.matched_rule == "key-only"
    assert decision.strategy == "rule"

    decision_b = asyncio.run(run(key_b))
    assert decision_b.model == "gpt-4o"
    assert decision_b.matched_rule is None
