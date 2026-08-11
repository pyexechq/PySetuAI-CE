import logging
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


def send_report_email(
    *,
    recipients: list[str],
    report_name: str,
    attachment_bytes: bytes,
    attachment_filename: str,
    attachment_mime: str,
    row_count: int,
) -> dict[str, Any]:
    cleaned = [r.strip() for r in recipients if r and r.strip()]
    if not cleaned:
        return {"status": "skipped", "reason": "no_recipients", "recipients": []}

    if not settings.smtp_enabled:
        logger.info(
            "SMTP disabled — report '%s' ready for %s (%s rows, %s bytes). Set SMTP_ENABLED=true to deliver.",
            report_name,
            ", ".join(cleaned),
            row_count,
            len(attachment_bytes),
        )
        return {"status": "skipped", "reason": "smtp_disabled", "recipients": cleaned}

    message = MIMEMultipart()
    message["Subject"] = f"PySetu Report: {report_name}"
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(cleaned)

    body = (
        f'Your scheduled PySetu report "{report_name}" is attached.\n\n'
        f"Records exported: {row_count:,}\n\n"
        f"— PySetu AI\n{settings.frontend_url}"
    )
    message.attach(MIMEText(body, "plain"))

    subtype = "pdf" if "pdf" in attachment_mime else "csv"
    attachment = MIMEApplication(attachment_bytes, _subtype=subtype)
    attachment.add_header("Content-Disposition", "attachment", filename=attachment_filename)
    message.attach(attachment)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_from, cleaned, message.as_string())
        logger.info("Delivered report '%s' to %s", report_name, ", ".join(cleaned))
        return {"status": "sent", "recipients": cleaned}
    except Exception as exc:
        logger.exception("Failed to send report email for '%s'", report_name)
        return {"status": "failed", "reason": str(exc), "recipients": cleaned}
