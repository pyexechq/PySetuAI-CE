from __future__ import annotations

from pydantic import BaseModel, Field


class HelpChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class HelpHighlightTarget(BaseModel):
    help_id: str
    label: str
    reason: str


class HelpChatLink(BaseModel):
    href: str
    label: str


class HelpChatRequest(BaseModel):
    message: str
    pathname: str = "/"
    search: str | None = None
    page_title: str | None = None
    page_description: str | None = None
    visible_help_ids: list[str] = Field(default_factory=list)
    history: list[HelpChatMessage] = Field(default_factory=list)


class HelpChatResponse(BaseModel):
    reply: str
    highlights: list[HelpHighlightTarget] = Field(default_factory=list)
    links: list[HelpChatLink] = Field(default_factory=list)
    ai_enhanced: bool = False
    page_label: str | None = None
