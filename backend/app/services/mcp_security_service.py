"""Persistence and enforcement helpers for MCP security controls."""

import re
import uuid
from collections.abc import Mapping

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.governance import MCPServer, McpSsoInjectionConfig, McpToolDenyRule

_HEADER_NAME = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]+$")
_CLAIM_NAME = re.compile(r"^[A-Za-z0-9_.-]*$")


def validate_sso_config(header_name: str, header_format: str, claim_extract: str) -> None:
    if not _HEADER_NAME.fullmatch(header_name.strip()):
        raise ValueError("Invalid HTTP header name")
    if header_format.count("{token}") != 1:
        raise ValueError("Header format must contain exactly one {token} placeholder")
    if not _CLAIM_NAME.fullmatch(claim_extract.strip()):
        raise ValueError("Invalid token claim name")


def injected_headers(config: McpSsoInjectionConfig, access_token: str, claims: Mapping[str, object] | None = None) -> dict[str, str]:
    if not config.enabled:
        return {}
    token = access_token
    if config.claim_extract:
        value = (claims or {}).get(config.claim_extract)
        if value is None or isinstance(value, (dict, list)):
            raise ValueError("Configured token claim is missing or not scalar")
        token = str(value)
    return {config.header_name: config.header_format.replace("{token}", token)}


async def get_sso_config(db: AsyncSession, tenant_id: uuid.UUID, server_id: uuid.UUID) -> McpSsoInjectionConfig | None:
    result = await db.execute(select(McpSsoInjectionConfig).where(McpSsoInjectionConfig.tenant_id == tenant_id, McpSsoInjectionConfig.server_id == server_id))
    return result.scalar_one_or_none()


async def upsert_sso_config(db: AsyncSession, tenant_id: uuid.UUID, server_id: uuid.UUID, **values: object) -> McpSsoInjectionConfig:
    header_name = str(values["header_name"]).strip()
    header_format = str(values["header_format"]).strip()
    claim_extract = str(values["claim_extract"]).strip()
    validate_sso_config(header_name, header_format, claim_extract)
    config = await get_sso_config(db, tenant_id, server_id)
    if config is None:
        config = McpSsoInjectionConfig(tenant_id=tenant_id, server_id=server_id)
        db.add(config)
    config.enabled = bool(values["enabled"])
    config.header_name, config.header_format, config.claim_extract = header_name, header_format, claim_extract
    await db.commit()
    await db.refresh(config)
    return config


async def list_deny_rules(db: AsyncSession, tenant_id: uuid.UUID) -> list[tuple[McpToolDenyRule, str]]:
    result = await db.execute(select(McpToolDenyRule, MCPServer.name).join(MCPServer, MCPServer.id == McpToolDenyRule.server_id).where(McpToolDenyRule.tenant_id == tenant_id).order_by(McpToolDenyRule.role, McpToolDenyRule.tool_name))
    return list(result.all())


async def add_deny_rule(db: AsyncSession, tenant_id: uuid.UUID, values: dict) -> McpToolDenyRule:
    row_values = {**values, "server_id": uuid.UUID(str(values["server_id"]))}
    rule = McpToolDenyRule(tenant_id=tenant_id, **row_values)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def remove_deny_rule(db: AsyncSession, tenant_id: uuid.UUID, rule_id: uuid.UUID) -> bool:
    result = await db.execute(delete(McpToolDenyRule).where(McpToolDenyRule.id == rule_id, McpToolDenyRule.tenant_id == tenant_id))
    await db.commit()
    return bool(result.rowcount)


def is_tool_denied(rules: list[McpToolDenyRule], role: str, server_id: uuid.UUID, tool_name: str) -> bool:
    return any(rule.role == role and rule.server_id == server_id and rule.tool_name.casefold() == tool_name.casefold() for rule in rules)