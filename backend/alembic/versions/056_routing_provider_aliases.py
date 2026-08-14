"""Routing rule target provider and model registry aliases."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "056_routing_provider_aliases"
down_revision: str | None = "055_ai_assist_base_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {col["name"] for col in inspect(bind).get_columns(table)}


def upgrade() -> None:
    if not _has_column("routing_rules", "target_provider"):
        op.add_column("routing_rules", sa.Column("target_provider", sa.String(length=64), nullable=True))

    if not _has_column("llm_providers", "model_aliases"):
        op.add_column(
            "llm_providers",
            sa.Column("model_aliases", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        )

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Migrate legacy UAG translation policies into routing rules.
    policies = bind.execute(
        text(
            """
            SELECT id, tenant_id, name, conditions, actions, priority, enabled
            FROM uag_translation_policies
            ORDER BY tenant_id, priority ASC
            """
        )
    ).mappings().all()

    for policy in policies:
        existing = bind.execute(
            text(
                """
                SELECT id FROM routing_rules
                WHERE tenant_id = :tenant_id AND name = :name
                LIMIT 1
                """
            ),
            {"tenant_id": policy["tenant_id"], "name": policy["name"]},
        ).first()
        if existing:
            continue

        from app.services.uag_migration_helpers import uag_conditions_to_routing_condition, uag_policy_to_routing_fields

        condition = uag_conditions_to_routing_condition(policy["conditions"] or {})
        target_model, target_provider, response_format = uag_policy_to_routing_fields(policy["actions"] or {})
        status = "active" if policy["enabled"] else "draft"

        bind.execute(
            text(
                """
                INSERT INTO routing_rules (
                    id, tenant_id, name, priority, condition, target_model, status, response_format, target_provider
                )
                VALUES (
                    gen_random_uuid(), :tenant_id, :name, :priority, :condition,
                    :target_model, :status, :response_format, :target_provider
                )
                """
            ),
            {
                "tenant_id": policy["tenant_id"],
                "name": policy["name"],
                "priority": policy["priority"],
                "condition": condition,
                "target_model": target_model,
                "status": status,
                "response_format": response_format,
                "target_provider": target_provider,
            },
        )

    mappings = bind.execute(
        text(
            """
            SELECT tenant_id, requested_model, actual_model, target_provider
            FROM uag_model_mappings
            WHERE enabled = true
            ORDER BY tenant_id, requested_model ASC
            """
        )
    ).mappings().all()

    for row in mappings:
        provider = bind.execute(
            text(
                """
                SELECT id, model_aliases
                FROM llm_providers
                WHERE tenant_id = :tenant_id AND lower(name) = lower(:actual_model)
                LIMIT 1
                """
            ),
            {"tenant_id": row["tenant_id"], "actual_model": row["actual_model"]},
        ).mappings().first()

        if provider:
            from app.services.uag_migration_helpers import merge_aliases

            aliases = merge_aliases(provider["model_aliases"], row["requested_model"])
            bind.execute(
                text("UPDATE llm_providers SET model_aliases = CAST(:aliases AS jsonb) WHERE id = :id"),
                {"aliases": __import__("json").dumps(aliases), "id": provider["id"]},
            )
            continue

        bind.execute(
            text(
                """
                INSERT INTO llm_providers (
                    id, tenant_id, name, provider_type, is_active, percentage,
                    avg_latency_ms, success_rate, cost_per_1m_input, cost_per_1m_output, model_aliases
                )
                VALUES (
                    gen_random_uuid(), :tenant_id, :name, :provider_type, true, 0,
                    0, 100, 0, 0, CAST(:aliases AS jsonb)
                )
                """
            ),
            {
                "tenant_id": row["tenant_id"],
                "name": row["actual_model"],
                "provider_type": row["target_provider"],
                "aliases": __import__("json").dumps([row["requested_model"]]),
            },
        )

    bind.execute(text("UPDATE uag_translation_policies SET enabled = false"))


def downgrade() -> None:
    if _has_column("llm_providers", "model_aliases"):
        op.drop_column("llm_providers", "model_aliases")
    if _has_column("routing_rules", "target_provider"):
        op.drop_column("routing_rules", "target_provider")
