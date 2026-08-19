"""Context-aware product help chat with optional AI enhancement."""

from __future__ import annotations

import json
import re
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.help_chat import HelpChatLink, HelpChatRequest, HelpChatResponse, HelpHighlightTarget
from app.schemas.openai import ChatMessage
from app.services.ai_assist_config_service import complete_ai_assist, resolve_ai_assist_config
from app.services.help_context_catalog import (
    CANONICAL_GUIDE_SLUGS,
    GUIDE_ARTICLE_SNIPPETS,
    HELP_TARGET_LABELS,
    normalize_guide_href,
    resolve_guide_slug,
    resolve_page_context,
)


def _extract_json(text: str) -> dict | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_links(links: list[HelpChatLink]) -> list[HelpChatLink]:
    normalized: list[HelpChatLink] = []
    seen: set[str] = set()
    for link in links:
        href = normalize_guide_href(link.href)
        if href in seen:
            continue
        seen.add(href)
        normalized.append(HelpChatLink(href=href, label=link.label))
    return normalized


def _page_guide_link(ctx: dict) -> HelpChatLink | None:
    guide_slug = ctx.get("guide_slug")
    if not guide_slug:
        return None
    resolved = resolve_guide_slug(str(guide_slug))
    if resolved not in CANONICAL_GUIDE_SLUGS:
        return None
    page_label = ctx["page_label"]
    return HelpChatLink(href=f"/help/guides/{resolved}", label=f"{page_label} guide")


def _filter_highlights(help_ids: list[str], visible: list[str]) -> list[str]:
    allowed = set(visible) if visible else set(help_ids)
    return [hid for hid in help_ids if hid in allowed]


def _deterministic_reply(request: HelpChatRequest, ctx: dict) -> HelpChatResponse:
    message = request.message.strip().lower()
    page_label = ctx["page_label"]
    tab = ctx.get("tab")
    tab_note = f" (tab: {tab})" if tab else ""

    highlights: list[HelpHighlightTarget] = []
    links: list[HelpChatLink] = []
    page_link = _page_guide_link(ctx)
    if page_link:
        links.append(page_link)

    if any(word in message for word in ("where", "find", "locate", "highlight", "show me")):
        if "create" in message and "prompt" in message:
            highlights.append(
                HelpHighlightTarget(
                    help_id="prompt-create-button",
                    label="Create template",
                    reason="Starts a new governed system prompt for gateway ingress.",
                )
            )
        elif "tab" in message or "section" in message:
            highlights.append(
                HelpHighlightTarget(
                    help_id="settings-group-nav",
                    label="Settings sections",
                    reason="Switch between workspace, AI & integrations, and access settings.",
                )
            )
        elif "date" in message or "range" in message or "time" in message:
            highlights.append(
                HelpHighlightTarget(
                    help_id="header-date-range",
                    label="Date range",
                    reason="Filters dashboard and monitoring metrics for the selected period.",
                )
            )
        elif "nav" in message or "menu" in message or "sidebar" in message:
            highlights.append(
                HelpHighlightTarget(
                    help_id="nav-sidebar",
                    label="Main navigation",
                    reason="Jump between gateway, governance, compliance, and settings modules.",
                )
            )
        elif ctx["page_key"] == "settings-prompts":
            highlights.append(
                HelpHighlightTarget(
                    help_id="prompt-template-list",
                    label="Templates table",
                    reason="Lists aliases, enforce modes, and versions for each system prompt.",
                )
            )

    if any(word in message for word in ("what is", "explain", "how does", "help", "overview")):
        reply = (
            f"You are on **{page_label}**{tab_note}. {ctx['summary']}\n\n"
            "Ask me to highlight a control (e.g. “where do I create a template?”) or open the product guide for step-by-step workflows."
        )
    elif highlights:
        reply = f"On **{page_label}**{tab_note} — here is what to use:"
    else:
        reply = (
            f"I can help you navigate **{page_label}**{tab_note}. Try asking:\n"
            "- “What is this page for?”\n"
            "- “Where do I create a prompt template?”\n"
            "- “Highlight the settings tabs”"
        )

    visible = request.visible_help_ids or ctx.get("help_ids", [])
    filtered = [
        h
        for h in highlights
        if h.help_id in visible or h.help_id in ctx.get("help_ids", [])
    ]

    return HelpChatResponse(
        reply=reply,
        highlights=filtered[:3],
        links=_normalize_links(links)[:2],
        ai_enhanced=False,
        page_label=page_label,
    )


async def build_help_chat_response(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    request: HelpChatRequest,
) -> HelpChatResponse:
    ctx = resolve_page_context(request.pathname, request.search)
    page_label = request.page_title or ctx["page_label"]
    ctx = {**ctx, "page_label": page_label}

    config = await resolve_ai_assist_config(db, tenant_id)
    if not config.available:
        return _deterministic_reply(request, ctx)

    target_catalog = "\n".join(
        f"- {hid}: {HELP_TARGET_LABELS.get(hid, hid)}"
        for hid in (request.visible_help_ids or ctx.get("help_ids", []))
    )
    guide_slug = ctx.get("guide_slug")
    guide_note = GUIDE_ARTICLE_SNIPPETS.get(guide_slug, "") if guide_slug else ""

    history_lines = "\n".join(f"{m.role}: {m.content}" for m in request.history[-6:])
    valid_slugs = ", ".join(sorted(CANONICAL_GUIDE_SLUGS))
    prompt = (
        "You are PySetu AI product help assistant. The user is inside the tenant web app.\n"
        "Return ONLY JSON with keys:\n"
        '- reply (string, markdown allowed, concise)\n'
        '- highlights (array of {help_id, label, reason}) — only use help_ids from the catalog below\n'
        '- links (array of {href, label}) — use ONLY /help/guides/{slug} with these exact slugs:\n'
        f"  {valid_slugs}\n"
        "  Never invent slugs like monitoring-overview; use monitoring instead.\n\n"
        f"Current page: {page_label}\n"
        f"Path: {request.pathname}\n"
        f"Query: {request.search or 'none'}\n"
        f"Description: {request.page_description or ctx['summary']}\n"
        f"Tab: {ctx.get('tab') or 'none'}\n"
        f"Guide context: {guide_note}\n\n"
        f"Highlight catalog (data-help-id):\n{target_catalog or '- none'}\n\n"
        f"Conversation:\n{history_lines}\n"
        f"User: {request.message}\n"
    )

    text, ok = await complete_ai_assist(config, [ChatMessage(role="user", content=prompt)], temperature=0.25)
    if not ok or not text:
        return _deterministic_reply(request, ctx)

    payload = _extract_json(text)
    if not payload:
        fallback = _deterministic_reply(request, ctx)
        fallback.reply = f"{text.strip()}\n\n---\n{fallback.reply}"
        fallback.ai_enhanced = True
        return fallback

    reply = str(payload.get("reply", "")).strip() or _deterministic_reply(request, ctx).reply
    visible = set(request.visible_help_ids or ctx.get("help_ids", []))
    highlights: list[HelpHighlightTarget] = []
    for item in payload.get("highlights", [])[:3]:
        if not isinstance(item, dict):
            continue
        help_id = str(item.get("help_id", "")).strip()
        if help_id and (not visible or help_id in visible):
            highlights.append(
                HelpHighlightTarget(
                    help_id=help_id,
                    label=str(item.get("label", HELP_TARGET_LABELS.get(help_id, help_id))),
                    reason=str(item.get("reason", "")),
                )
            )

    links: list[HelpChatLink] = []
    seen_hrefs: set[str] = set()
    for item in payload.get("links", [])[:4]:
        if not isinstance(item, dict):
            continue
        href = str(item.get("href", "")).strip()
        label = str(item.get("label", "")).strip()
        if href and label and href not in seen_hrefs:
            seen_hrefs.add(href)
            links.append(HelpChatLink(href=href, label=label))

    if page_link := _page_guide_link(ctx):
        if not any(l.href == page_link.href for l in links):
            links.insert(0, page_link)

    return HelpChatResponse(
        reply=reply,
        highlights=highlights,
        links=_normalize_links(links),
        ai_enhanced=True,
        page_label=page_label,
    )
