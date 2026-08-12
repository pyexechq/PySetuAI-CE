import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class PromptVersionBase(BaseModel):
    system_prompt: str = Field(..., description="System prompt template text containing {{var}} placeholders")


class PromptVersionCreate(PromptVersionBase):
    pass


class PromptVersionResponse(PromptVersionBase):
    id: uuid.UUID
    template_id: uuid.UUID
    version: int
    variables: list[str] = Field(default_factory=list)
    created_by: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class PromptTemplateCreate(BaseModel):
    name: str = Field(..., max_length=128)
    alias: str | None = Field(None, max_length=64)
    description: str | None = None
    enforce_mode: str = Field("warn", description="strict, warn, or disabled")
    system_prompt: str = Field(..., description="Initial version system prompt")


class PromptTemplateUpdate(BaseModel):
    name: str | None = None
    alias: str | None = None
    description: str | None = None
    enforce_mode: str | None = None
    is_active: bool | None = None


class PromptTemplateResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    alias: str | None = None
    description: str | None = None
    enforce_mode: str
    is_active: bool
    current_version_id: uuid.UUID | None = None
    current_version: PromptVersionResponse | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
