"""SMTP configuration management for platform operators (SaaS) and individual tenants."""

from __future__ import annotations

import logging
import smtplib
import uuid
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.tenant import Tenant
from app.schemas.smtp import SmtpConfigResponse, SmtpConfigUpdate, SmtpTestRequest, SmtpTestResponse
from app.services.integration_service import mask_secret
from app.services.secrets_service import get_tenant_secret, set_tenant_secret

logger = logging.getLogger(__name__)

SMTP_PASSWORD_SECRET = "smtp_password"
SMTP_FLAGS_KEY = "smtp_config"


def _empty_smtp_dict() -> dict[str, Any]:
    return {
        "enabled": False,
        "host": "",
        "port": 587,
        "from_email": "",
        "from_name": "PySetu AI",
        "username": "",
        "use_tls": True,
        "use_ssl": False,
    }


async def _get_platform_tenant(db: AsyncSession) -> Tenant | None:
    platform_slug = settings.platform_tenant_slug.strip().lower()
    result = await db.execute(select(Tenant).where(Tenant.slug == platform_slug))
    return result.scalar_one_or_none()


async def get_platform_smtp_config(db: AsyncSession) -> SmtpConfigResponse:
    """Retrieve global platform SMTP configuration (used for SaaS platform admin & fallback)."""
    platform_tenant = await _get_platform_tenant(db)
    
    stored: dict[str, Any] = {}
    password_val: str | None = None

    if platform_tenant is not None:
        flags = getattr(platform_tenant, "feature_flags", None)
        if isinstance(flags, dict) and SMTP_FLAGS_KEY in flags and isinstance(flags[SMTP_FLAGS_KEY], dict):
            stored = flags[SMTP_FLAGS_KEY]
        password_val = await get_tenant_secret(db, platform_tenant.id, SMTP_PASSWORD_SECRET)

    # Determine values with environment fallback
    has_stored = bool(stored.get("host") or stored.get("from_email"))
    
    enabled = bool(stored.get("enabled", settings.smtp_enabled if not has_stored else False))
    host = str(stored.get("host") or (settings.smtp_host if not has_stored else ""))
    port = int(stored.get("port") or (settings.smtp_port if not has_stored else 587))
    from_email = str(stored.get("from_email") or (settings.smtp_from if not has_stored else ""))
    from_name = str(stored.get("from_name") or "PySetu AI")
    username = str(stored.get("username") or (settings.smtp_user if not has_stored else ""))
    use_tls = bool(stored.get("use_tls", settings.smtp_use_tls if not has_stored else True))
    use_ssl = bool(stored.get("use_ssl", False))

    if not password_val and not has_stored and settings.smtp_password:
        password_val = settings.smtp_password

    return SmtpConfigResponse(
        enabled=enabled,
        host=host,
        port=port,
        from_email=from_email,
        from_name=from_name,
        username=username,
        password_set=bool(password_val),
        password_masked=mask_secret(password_val),
        use_tls=use_tls,
        use_ssl=use_ssl,
        is_custom=False,
        source="platform_configured" if has_stored else "environment_fallback",
        info_message="Configured platform-wide default SMTP for SaaS invites, notifications, and alerts.",
    )


async def update_platform_smtp_config(
    db: AsyncSession, payload: SmtpConfigUpdate
) -> SmtpConfigResponse:
    """Save global platform SMTP configuration."""
    platform_tenant = await _get_platform_tenant(db)
    if platform_tenant is None:
        raise ValueError(f"Platform tenant '{settings.platform_tenant_slug}' not found")

    flags = dict(platform_tenant.feature_flags or {})
    current_smtp = dict(flags.get(SMTP_FLAGS_KEY) or _empty_smtp_dict())

    if payload.enabled is not None:
        current_smtp["enabled"] = payload.enabled
    if payload.host is not None:
        current_smtp["host"] = payload.host.strip()
    if payload.port is not None:
        current_smtp["port"] = payload.port
    if payload.from_email is not None:
        current_smtp["from_email"] = payload.from_email.strip()
    if payload.from_name is not None:
        current_smtp["from_name"] = payload.from_name.strip()
    if payload.username is not None:
        current_smtp["username"] = payload.username.strip()
    if payload.use_tls is not None:
        current_smtp["use_tls"] = payload.use_tls
    if payload.use_ssl is not None:
        current_smtp["use_ssl"] = payload.use_ssl

    flags[SMTP_FLAGS_KEY] = current_smtp
    platform_tenant.feature_flags = flags

    if payload.password is not None:
        clean_pass = payload.password.strip() or None
        await set_tenant_secret(db, platform_tenant.id, SMTP_PASSWORD_SECRET, clean_pass)

    await db.commit()
    await db.refresh(platform_tenant)
    return await get_platform_smtp_config(db)


async def get_tenant_smtp_config(db: AsyncSession, tenant_id: uuid.UUID) -> SmtpConfigResponse:
    """Retrieve tenant-specific SMTP configuration or fall back to platform settings."""
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("Tenant not found")

    flags = getattr(tenant, "feature_flags", None) or {}
    tenant_smtp = flags.get(SMTP_FLAGS_KEY) if isinstance(flags, dict) else None

    # If tenant has explicitly configured SMTP
    if isinstance(tenant_smtp, dict) and bool(tenant_smtp.get("host") or tenant_smtp.get("from_email")):
        password_val = await get_tenant_secret(db, tenant_id, SMTP_PASSWORD_SECRET)
        return SmtpConfigResponse(
            enabled=bool(tenant_smtp.get("enabled", False)),
            host=str(tenant_smtp.get("host", "")),
            port=int(tenant_smtp.get("port", 587)),
            from_email=str(tenant_smtp.get("from_email", "")),
            from_name=str(tenant_smtp.get("from_name", tenant.display_name or tenant.name or "PySetu AI")),
            username=str(tenant_smtp.get("username", "")),
            password_set=bool(password_val),
            password_masked=mask_secret(password_val),
            use_tls=bool(tenant_smtp.get("use_tls", True)),
            use_ssl=bool(tenant_smtp.get("use_ssl", False)),
            is_custom=True,
            source="tenant_custom",
            info_message="Tenant custom SMTP is active. Outbound emails will be delivered via your configured server.",
        )

    # Fall back to platform SMTP
    platform_resp = await get_platform_smtp_config(db)
    return SmtpConfigResponse(
        enabled=platform_resp.enabled,
        host=platform_resp.host,
        port=platform_resp.port,
        from_email=platform_resp.from_email,
        from_name=tenant.display_name or tenant.name or platform_resp.from_name,
        username=platform_resp.username,
        password_set=platform_resp.password_set,
        password_masked=platform_resp.password_masked,
        use_tls=platform_resp.use_tls,
        use_ssl=platform_resp.use_ssl,
        is_custom=False,
        source=platform_resp.source,
        info_message="Currently using Platform SaaS SMTP defaults. Toggle 'Enable Custom SMTP' below to override with your organization's mail server.",
    )


async def update_tenant_smtp_config(
    db: AsyncSession, tenant_id: uuid.UUID, payload: SmtpConfigUpdate
) -> SmtpConfigResponse:
    """Update tenant-specific SMTP configuration."""
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("Tenant not found")

    flags = dict(tenant.feature_flags or {})
    current_smtp = dict(flags.get(SMTP_FLAGS_KEY) or _empty_smtp_dict())

    if payload.enabled is not None:
        current_smtp["enabled"] = payload.enabled
    if payload.host is not None:
        current_smtp["host"] = payload.host.strip()
    if payload.port is not None:
        current_smtp["port"] = payload.port
    if payload.from_email is not None:
        current_smtp["from_email"] = payload.from_email.strip()
    if payload.from_name is not None:
        current_smtp["from_name"] = payload.from_name.strip()
    if payload.username is not None:
        current_smtp["username"] = payload.username.strip()
    if payload.use_tls is not None:
        current_smtp["use_tls"] = payload.use_tls
    if payload.use_ssl is not None:
        current_smtp["use_ssl"] = payload.use_ssl

    flags[SMTP_FLAGS_KEY] = current_smtp
    tenant.feature_flags = flags

    if payload.password is not None:
        clean_pass = payload.password.strip() or None
        await set_tenant_secret(db, tenant_id, SMTP_PASSWORD_SECRET, clean_pass)

    await db.commit()
    await db.refresh(tenant)
    return await get_tenant_smtp_config(db, tenant_id)


async def resolve_effective_smtp_credentials(
    db: AsyncSession, tenant_id: uuid.UUID | None = None
) -> dict[str, Any]:
    """Resolve full operational SMTP connection credentials including decrypted password."""
    # 1. Check tenant custom SMTP
    if tenant_id:
        tenant = await db.get(Tenant, tenant_id)
        if tenant:
            flags = getattr(tenant, "feature_flags", None) or {}
            tenant_smtp = flags.get(SMTP_FLAGS_KEY)
            if isinstance(tenant_smtp, dict) and bool(tenant_smtp.get("host") or tenant_smtp.get("from_email")):
                password = await get_tenant_secret(db, tenant_id, SMTP_PASSWORD_SECRET)
                return {
                    "enabled": bool(tenant_smtp.get("enabled", False)),
                    "host": tenant_smtp.get("host", ""),
                    "port": int(tenant_smtp.get("port", 587)),
                    "from_email": tenant_smtp.get("from_email") or settings.smtp_from,
                    "from_name": tenant_smtp.get("from_name") or tenant.display_name or tenant.name or "PySetu AI",
                    "username": tenant_smtp.get("username") or "",
                    "password": password or "",
                    "use_tls": bool(tenant_smtp.get("use_tls", True)),
                    "use_ssl": bool(tenant_smtp.get("use_ssl", False)),
                    "source": "tenant_custom",
                }

    # 2. Check Platform Tenant SMTP
    platform_tenant = await _get_platform_tenant(db)
    if platform_tenant:
        flags = getattr(platform_tenant, "feature_flags", None) or {}
        p_smtp = flags.get(SMTP_FLAGS_KEY)
        if isinstance(p_smtp, dict) and bool(p_smtp.get("host") or p_smtp.get("from_email")):
            password = await get_tenant_secret(db, platform_tenant.id, SMTP_PASSWORD_SECRET)
            return {
                "enabled": bool(p_smtp.get("enabled", False)),
                "host": p_smtp.get("host", ""),
                "port": int(p_smtp.get("port", 587)),
                "from_email": p_smtp.get("from_email") or settings.smtp_from,
                "from_name": p_smtp.get("from_name") or "PySetu AI",
                "username": p_smtp.get("username") or "",
                "password": password or "",
                "use_tls": bool(p_smtp.get("use_tls", True)),
                "use_ssl": bool(p_smtp.get("use_ssl", False)),
                "source": "platform_configured",
            }

    # 3. Fallback to settings / environment
    return {
        "enabled": settings.smtp_enabled,
        "host": settings.smtp_host,
        "port": settings.smtp_port,
        "from_email": settings.smtp_from,
        "from_name": "PySetu AI",
        "username": settings.smtp_user or "",
        "password": settings.smtp_password or "",
        "use_tls": settings.smtp_use_tls,
        "use_ssl": False,
        "source": "environment_fallback",
    }


def send_smtp_message(
    *,
    config: dict[str, Any],
    recipients: list[str],
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> dict[str, Any]:
    """Low-level SMTP message delivery using resolved credentials and smart TLS/SSL negotiation."""
    import ssl

    cleaned = [r.strip() for r in recipients if r and r.strip()]
    if not cleaned:
        return {"status": "skipped", "reason": "no_recipients", "recipients": []}

    if not config.get("enabled"):
        logger.info("SMTP is disabled in configuration. Skipping delivery to %s", ", ".join(cleaned))
        return {"status": "skipped", "reason": "smtp_disabled", "recipients": cleaned}

    host = config.get("host")
    if not host:
        return {"status": "failed", "reason": "SMTP host not configured", "recipients": cleaned}

    port = int(config.get("port", 587))
    use_tls = bool(config.get("use_tls", True))
    use_ssl = bool(config.get("use_ssl", False))
    from_email = config.get("from_email") or settings.smtp_from
    from_name = config.get("from_name") or "PySetu AI"
    username = config.get("username")
    password = config.get("password")

    from_header = f'"{from_name}" <{from_email}>' if from_name else from_email

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = from_header
    message["To"] = ", ".join(cleaned)

    plain = text_body or html_body
    message.attach(MIMEText(plain, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    # Determine whether to use direct SSL (implicit SSL on port 465) or STARTTLS (port 587 / 25)
    # Port 465 standard is direct SSL. Port 587 standard is STARTTLS.
    should_use_direct_ssl = (port == 465) or (use_ssl and port != 587)

    server = None
    ssl_context = ssl.create_default_context()

    try:
        if should_use_direct_ssl:
            try:
                server = smtplib.SMTP_SSL(host, port, timeout=25, context=ssl_context)
                server.ehlo()
            except (ssl.SSLError, ConnectionResetError) as ssl_err:
                logger.warning(
                    "Direct SMTP_SSL on %s:%s failed with %s, falling back to STARTTLS",
                    host, port, ssl_err
                )
                server = smtplib.SMTP(host, port, timeout=25)
                server.ehlo()
                if use_tls:
                    server.starttls(context=ssl_context)
                    server.ehlo()
        else:
            try:
                server = smtplib.SMTP(host, port, timeout=25)
                server.ehlo()
                if use_tls or port == 587:
                    try:
                        server.starttls(context=ssl_context)
                        server.ehlo()
                    except smtplib.SMTPNotSupportedError:
                        logger.warning("STARTTLS not supported on %s:%s, continuing without TLS", host, port)
            except (ssl.SSLError, ConnectionResetError) as ssl_err:
                if "WRONG_VERSION_NUMBER" in str(ssl_err) or port == 465:
                    logger.warning(
                        "STARTTLS on %s:%s failed with %s, attempting SMTP_SSL fallback",
                        host, port, ssl_err
                    )
                    server = smtplib.SMTP_SSL(host, port, timeout=25, context=ssl_context)
                    server.ehlo()
                else:
                    raise

        with server:
            if username:
                if not password:
                    return {
                        "status": "failed",
                        "reason": "SMTP Username was provided but Password is empty. Please enter your email account password.",
                        "recipients": cleaned,
                    }
                server.login(username, password)
            elif password:
                return {
                    "status": "failed",
                    "reason": "SMTP Password was provided without a Username. Please provide your full email address as username.",
                    "recipients": cleaned,
                }
            server.sendmail(from_email, cleaned, message.as_string())

        logger.info("Successfully sent SMTP email '%s' to %s via %s:%s", subject, ", ".join(cleaned), host, port)
        return {"status": "sent", "recipients": cleaned, "host": host, "port": port}
    except smtplib.SMTPAuthenticationError as auth_err:
        logger.warning("SMTP Authentication failed: %s", auth_err)
        return {
            "status": "failed",
            "reason": f"Authentication Failed (535): Invalid username or password. Ensure your username is your full email address ({from_email}) and your password is correct.",
            "recipients": cleaned,
        }
    except smtplib.SMTPSenderRefused as sender_err:
        logger.warning("SMTP Sender refused: %s", sender_err)
        return {
            "status": "failed",
            "reason": f"Sender Address Refused ({sender_err.smtp_code}): The mail server rejected sending from '{from_email}'. Ensure 'From Email Address' exactly matches your authenticated username.",
            "recipients": cleaned,
        }
    except smtplib.SMTPRecipientsRefused as recip_err:
        logger.warning("SMTP Recipient refused: %s", recip_err)
        # Check if error is 554 5.7.1 Access denied (often means unauthenticated or from mismatch)
        err_msg = str(recip_err)
        if "5.7.1" in err_msg and "Access denied" in err_msg:
            return {
                "status": "failed",
                "reason": f"Relay Access Denied (554 5.7.1): Hostinger/Mail server rejected unauthenticated relay. Please ensure: 1) SMTP Username is your full email address ({from_email or 'user@domain'}), 2) Password is saved, and 3) 'From Email Address' matches the Username.",
                "recipients": cleaned,
            }
        return {
            "status": "failed",
            "reason": f"Recipient Refused: {recip_err}",
            "recipients": cleaned,
        }
    except Exception as exc:
        logger.exception("SMTP transmission failure to %s: %s", ", ".join(cleaned), exc)
        return {"status": "failed", "reason": str(exc), "recipients": cleaned}


async def test_smtp_configuration(
    db: AsyncSession,
    tenant_id: uuid.UUID | None,
    payload: SmtpTestRequest,
) -> SmtpTestResponse:
    """Send a test email using either provided parameters or saved configuration."""
    # 1. Base on effective config
    effective = await resolve_effective_smtp_credentials(db, tenant_id)

    # 2. Apply any override fields from the test request
    if payload.host is not None and payload.host.strip():
        effective["host"] = payload.host.strip()
        effective["enabled"] = True
    if payload.port is not None:
        effective["port"] = payload.port
    if payload.from_email is not None and payload.from_email.strip():
        effective["from_email"] = payload.from_email.strip()
    if payload.from_name is not None and payload.from_name.strip():
        effective["from_name"] = payload.from_name.strip()
    if payload.username is not None:
        effective["username"] = payload.username.strip()
    if payload.password is not None and payload.password.strip():
        effective["password"] = payload.password.strip()
    if payload.use_tls is not None:
        effective["use_tls"] = payload.use_tls
    if payload.use_ssl is not None:
        effective["use_ssl"] = payload.use_ssl

    effective["enabled"] = True  # Always enable for testing

    test_time = datetime.now(UTC).strftime("%B %d, %Y %H:%M:%S UTC")
    subject = f"PySetu AI — SMTP Configuration Test ({test_time})"
    html_body = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #0b1120; color: #f8fafc; padding: 32px 16px;">
  <div style="max-width: 560px; margin: 0 auto; background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 28px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
    <div style="display: flex; align-items: center; margin-bottom: 20px;">
      <h1 style="color: #38bdf8; margin: 0; font-size: 20px; font-weight: 700;">PySetu AI Control Plane</h1>
    </div>
    <div style="background-color: #0284c715; border: 1px solid #0284c740; border-radius: 8px; padding: 14px; margin-bottom: 20px;">
      <p style="margin: 0; color: #38bdf8; font-weight: 600; font-size: 15px;">✓ SMTP Connection Verified Successfully</p>
    </div>
    <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin-bottom: 16px;">
      This is a test notification confirming that your SMTP mail server credentials are functional and ready for transactional email delivery.
    </p>
    <table style="width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 13px; color: #94a3b8;">
      <tr>
        <td style="padding: 6px 0; border-bottom: 1px solid #334155;"><strong>Host:</strong></td>
        <td style="padding: 6px 0; border-bottom: 1px solid #334155; color: #f8fafc;">{effective.get('host')}</td>
      </tr>
      <tr>
        <td style="padding: 6px 0; border-bottom: 1px solid #334155;"><strong>Port:</strong></td>
        <td style="padding: 6px 0; border-bottom: 1px solid #334155; color: #f8fafc;">{effective.get('port')}</td>
      </tr>
      <tr>
        <td style="padding: 6px 0; border-bottom: 1px solid #334155;"><strong>From Address:</strong></td>
        <td style="padding: 6px 0; border-bottom: 1px solid #334155; color: #f8fafc;">{effective.get('from_email')}</td>
      </tr>
      <tr>
        <td style="padding: 6px 0; border-bottom: 1px solid #334155;"><strong>TLS Mode:</strong></td>
        <td style="padding: 6px 0; border-bottom: 1px solid #334155; color: #f8fafc;">{'STARTTLS' if effective.get('use_tls') else ('SSL' if effective.get('use_ssl') else 'Plaintext')}</td>
      </tr>
      <tr>
        <td style="padding: 6px 0;"><strong>Timestamp:</strong></td>
        <td style="padding: 6px 0; color: #f8fafc;">{test_time}</td>
      </tr>
    </table>
  </div>
</body>
</html>"""

    result = send_smtp_message(
        config=effective,
        recipients=[payload.recipient_email],
        subject=subject,
        html_body=html_body,
    )

    if result.get("status") == "sent":
        return SmtpTestResponse(
            success=True,
            message=f"Test email successfully sent to {payload.recipient_email} via {effective.get('host')}:{effective.get('port')}",
            details=result,
        )
    return SmtpTestResponse(
        success=False,
        message=f"SMTP Delivery failed: {result.get('reason', 'Unknown error')}",
        details=result,
    )
