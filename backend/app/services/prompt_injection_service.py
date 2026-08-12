import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.governance import PromptTemplate
from app.schemas.openai import ChatMessage


def apply_variable_substitution(template_text: str, variables: dict[str, Any] | None = None) -> str:
    if not variables:
        # Strip unfilled placeholders or leave clean
        return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", "", template_text).strip()

    result = template_text
    for key, value in variables.items():
        pattern = r"\{\{\s*" + re.escape(key) + r"\s*\}\}"
        result = re.sub(pattern, str(value), result)
    # Clear any remaining unfilled placeholders
    return re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", "", result).strip()


async def resolve_and_inject_prompt(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    messages: list[ChatMessage],
    requested_template: str | None = None,
    variables: dict[str, Any] | None = None,
) -> tuple[list[ChatMessage], str | None, int | None, str | None, str | None, bool]:
    """
    Returns: (modified_messages, template_id, version_num, enforce_mode, warning_message, is_blocked)
    """
    # 1. Fetch active templates for tenant
    stmt = (
        select(PromptTemplate)
        .options(selectinload(PromptTemplate.versions))
        .where(PromptTemplate.tenant_id == tenant_id, PromptTemplate.is_active.is_(True))
    )
    result = await db.execute(stmt)
    templates = result.scalars().all()

    matched_template: PromptTemplate | None = None
    if requested_template:
        for t in templates:
            if str(t.id) == requested_template or t.alias == requested_template or t.name == requested_template:
                matched_template = t
                break

    has_strict_template = any(t.enforce_mode == "strict" for t in templates)
    has_adhoc_system_message = any(m.role == "system" for m in messages)

    # 2. If template matched, inject versioned system prompt
    if matched_template:
        curr_ver = None
        if matched_template.versions:
            curr_ver = next(
                (v for v in matched_template.versions if v.id == matched_template.current_version_id),
                matched_template.versions[-1],
            )

        if curr_ver:
            substituted_prompt = apply_variable_substitution(curr_ver.system_prompt, variables)
            new_messages = []
            system_injected = False
            for msg in messages:
                if msg.role == "system" and not system_injected:
                    new_messages.append(ChatMessage(role="system", content=substituted_prompt))
                    system_injected = True
                elif msg.role != "system":
                    new_messages.append(msg)

            if not system_injected:
                new_messages.insert(0, ChatMessage(role="system", content=substituted_prompt))

            return (
                new_messages,
                str(matched_template.id),
                curr_ver.version,
                matched_template.enforce_mode,
                None,
                False,
            )

    # 3. If no template matched but tenant enforces strict prompt policy on ad-hoc prompts
    if has_adhoc_system_message and has_strict_template:
        return (
            messages,
            None,
            None,
            "strict",
            "Ad-hoc system prompts are blocked by tenant policy. Please use a managed prompt template.",
            True,
        )

    warning_msg = None
    if has_adhoc_system_message:
        warning_msg = "Ad-hoc system prompt used without managed prompt template."

    return (messages, None, None, None, warning_msg, False)
