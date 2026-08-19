"""Tests for help guide slug resolution and help chat."""

import pytest

from app.schemas.help_chat import HelpChatLink, HelpChatRequest
from app.services.help_assist_service import _deterministic_reply, _normalize_links
from app.services.help_context_catalog import (
    normalize_guide_href,
    resolve_guide_slug,
    resolve_page_context,
)


def test_resolve_page_context_prompts():
    ctx = resolve_page_context("/settings/prompts")
    assert ctx["page_key"] == "settings-prompts"


def test_resolve_guide_slug_monitoring_overview_alias():
    assert resolve_guide_slug("monitoring-overview") == "monitoring"


def test_normalize_guide_href_monitoring_overview():
    assert normalize_guide_href("/help/guides/monitoring-overview") == "/help/guides/monitoring"


def test_normalize_guide_href_unknown_falls_back_to_help_hub():
    assert normalize_guide_href("/help/guides/not-a-real-guide") == "/help?tab=guides"


def test_normalize_links_dedupes_after_alias():
    links = _normalize_links(
        [
            HelpChatLink(href="/help/guides/monitoring-overview", label="Overview"),
            HelpChatLink(href="/help/guides/monitoring", label="Monitoring"),
        ]
    )
    assert len(links) == 1
    assert links[0].href == "/help/guides/monitoring"


def test_deterministic_reply_highlights_create_template():
    ctx = resolve_page_context("/settings/prompts")
    request = HelpChatRequest(
        message="Where do I create a prompt template?",
        pathname="/settings/prompts",
        visible_help_ids=["prompt-create-button", "prompt-template-list"],
    )
    response = _deterministic_reply(request, ctx)
    assert response.highlights
    assert response.highlights[0].help_id == "prompt-create-button"
