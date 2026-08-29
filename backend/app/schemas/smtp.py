from __future__ import annotations

from pydantic import BaseModel, Field


class SmtpConfigResponse(BaseModel):
    enabled: bool = False
    host: str = ""
    port: int = 587
    from_email: str = ""
    from_name: str = "PySetu AI"
    username: str = ""
    password_set: bool = False
    password_masked: str | None = None
    use_tls: bool = True
    use_ssl: bool = False
    is_custom: bool = False
    source: str = "platform_default"  # "tenant_custom", "platform_configured", or "environment_fallback"
    info_message: str | None = None


class SmtpConfigUpdate(BaseModel):
    enabled: bool | None = None
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    from_email: str | None = None
    from_name: str | None = None
    username: str | None = None
    password: str | None = Field(default=None, description="Set empty string to clear password")
    use_tls: bool | None = None
    use_ssl: bool | None = None


class SmtpTestRequest(BaseModel):
    recipient_email: str = Field(..., description="Email address to send the test message to")
    # Optional override parameters to test before saving
    host: str | None = None
    port: int | None = None
    from_email: str | None = None
    from_name: str | None = None
    username: str | None = None
    password: str | None = None
    use_tls: bool | None = None
    use_ssl: bool | None = None


class SmtpTestResponse(BaseModel):
    success: bool
    message: str
    details: dict | None = None
