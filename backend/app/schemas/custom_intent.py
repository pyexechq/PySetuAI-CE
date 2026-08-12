import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CustomIntentCreate(BaseModel):
    name: str = Field(..., max_length=128, description="Name of the custom intent classifier")
    description: Optional[str] = Field(None, description="Optional description of intent focus area")
    action: str = Field("block", description="Policy action on intent match: block, monitor, or redact")
    keywords: List[str] = Field(default_factory=list, description="Sample phrases or keywords for topic matching")
    confidence_threshold: float = Field(0.8, ge=0.0, le=1.0, description="Minimum confidence score threshold (0.0 to 1.0)")
    is_active: bool = Field(True, description="Whether this classifier is active")
    parent_id: Optional[uuid.UUID] = Field(None, description="Parent folder ID")
    intent_type: str = Field("intent", description="Type of node: 'intent' or 'folder'")


class CustomIntentUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    description: Optional[str] = None
    action: Optional[str] = None
    keywords: Optional[List[str]] = None
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    is_active: Optional[bool] = None
    parent_id: Optional[uuid.UUID] = None
    intent_type: Optional[str] = None


class CustomIntentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: Optional[str] = None
    action: str
    keywords: List[str]
    confidence_threshold: float
    is_active: bool
    parent_id: Optional[uuid.UUID] = None
    intent_type: str = "intent"
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CustomIntentTestRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Prompt text to test against active custom intents")
    intent_ids: Optional[List[uuid.UUID]] = Field(None, description="Optional filter of specific custom intent IDs to test")


class CustomIntentMatch(BaseModel):
    intent_id: uuid.UUID
    intent_name: str
    action: str
    matched_keywords: List[str]
    score: float


class CustomIntentTestResponse(BaseModel):
    matched: bool
    matches: List[CustomIntentMatch]
    action: str  # "block", "monitor", "redact", or "allow"
    modified_prompt: Optional[str] = None


class CustomIntentAssistRequest(BaseModel):
    goal: str = Field(..., description="User's plain text goal for a new intent classifier")


class CustomIntentAssistSuggestion(BaseModel):
    name: str
    description: str
    action: str
    keywords: List[str]
    confidence_threshold: float


class CustomIntentAssistResponse(BaseModel):
    summary: str
    ai_enhanced: bool = False
    suggestions: List[CustomIntentAssistSuggestion]

