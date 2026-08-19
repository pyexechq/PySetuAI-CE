from pydantic import BaseModel, Field


class AlertWebhookCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    webhook_type: str = Field(default="slack", max_length=32)
    endpoint_url: str = Field(..., min_length=1, max_length=1024)
    auth_token: str | None = Field(default=None, max_length=4096)
    channel: str | None = Field(default=None, max_length=128)
    enabled: bool = True
    config_json: dict | None = None
    dispatch_policy: dict | None = None


class AlertWebhookUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    webhook_type: str | None = Field(default=None, max_length=32)
    endpoint_url: str | None = Field(default=None, min_length=1, max_length=1024)
    auth_token: str | None = Field(default=None, max_length=4096)
    channel: str | None = Field(default=None, max_length=128)
    enabled: bool | None = None
    config_json: dict | None = None
    dispatch_policy: dict | None = None


class AlertWebhookResponse(BaseModel):
    id: str
    name: str
    webhook_type: str
    endpoint_url: str
    channel: str | None = None
    enabled: bool
    alerts_sent: int
    tickets_created: int = 0
    last_alert_at: str | None = None
    last_error: str = ""
    config_json: dict | None = None
    dispatch_policy: dict | None = None
    auth_token_set: bool = False
    auth_token_masked: str | None = None


class AlertWebhookTestResponse(BaseModel):
    webhook_id: str
    webhook_name: str
    message: str
