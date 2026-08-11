"""Tests for invite email template rendering."""

from app.services.invite_email_template_service import render_template_string, sample_preview_context


def test_render_template_string_replaces_variables() -> None:
    context = sample_preview_context()
    rendered = render_template_string("Hello {{admin_name}} at {{tenant_name}}", context)
    assert "Alex Admin" in rendered
    assert "Globex Industries" in rendered


def test_render_template_string_keeps_unknown_placeholders() -> None:
    rendered = render_template_string("Hello {{unknown_var}}", {"admin_name": "Alex"})
    assert rendered == "Hello {{unknown_var}}"
