"""Shared SMTP delivery for transactional platform emails."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def send_email(
    *,
    recipients: list[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> dict[str, Any]:
    cleaned = [recipient.strip() for recipient in recipients if recipient and recipient.strip()]
    if not cleaned:
        return {"status": "skipped", "reason": "no_recipients", "recipients": []}

    if not settings.smtp_enabled:
        logger.info(
            "SMTP disabled — email '%s' ready for %s. Set SMTP_ENABLED=true to deliver.",
            subject,
            ", ".join(cleaned),
        )
        return {"status": "skipped", "reason": "smtp_disabled", "recipients": cleaned}

    plain = text_body or _html_to_plain(html_body)
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(cleaned)
    message.attach(MIMEText(plain, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from, cleaned, message.as_string())
        logger.info("Delivered email '%s' to %s", subject, ", ".join(cleaned))
        return {"status": "sent", "recipients": cleaned}
    except Exception as exc:
        logger.exception("Failed to send email '%s'", subject)
        return {"status": "failed", "reason": str(exc), "recipients": cleaned}


def _html_to_plain(html: str) -> str:
    text = html.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    for tag in ("<p>", "</p>", "<div>", "</div>", "<li>", "</li>"):
        text = text.replace(tag, "\n" if tag.startswith("</") else "")
    while "<" in text and ">" in text:
        start = text.find("<")
        end = text.find(">", start)
        if end == -1:
            break
        text = text[:start] + text[end + 1 :]
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
