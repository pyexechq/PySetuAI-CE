from datetime import datetime

from pydantic import BaseModel, Field


class ClaudeComplianceRecord(BaseModel):
    organization_id: str = Field(..., min_length=1, max_length=255)
    user_id: str = Field(..., min_length=1, max_length=255)
    chat_id: str = Field(..., min_length=1, max_length=255)
    content: str = Field(default="", max_length=32000)
    action: str = Field(default="chat.sync", max_length=100)
    status: str = Field(default="observed", pattern="^(observed|blocked|review)$")
    timestamp: datetime | None = None


class ClaudeComplianceSyncRequest(BaseModel):
    records: list[ClaudeComplianceRecord] = Field(min_length=1, max_length=500)


class ClaudeComplianceSyncResponse(BaseModel):
    source: str
    records_received: int
    records_synced: int
    users_synced: int
    chats_synced: int
    dlp_matches: int
    classifications: dict[str, int]