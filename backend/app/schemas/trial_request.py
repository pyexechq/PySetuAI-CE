import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class TrialRequestCreate(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=128, description="Contact person full name")
    work_email: EmailStr = Field(..., description="Corporate/work email address")
    company_name: str = Field(..., min_length=2, max_length=255, description="Organization or company name")
    team_size: str | None = Field(default="1-20", description="Team size or expected AI workloads")
    use_case: str | None = Field(default="AI Gateway & Governance", description="Primary AI governance use case")
    message: str | None = Field(default=None, max_length=2000, description="Optional notes or requirements")


class TrialRequestResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    work_email: str
    company_name: str
    team_size: str | None
    use_case: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class TrialSubmissionResult(BaseModel):
    success: bool = True
    message: str = "Thank you! Your 30-day trial request has been received. Our team will provision your dedicated tenant and send your access details shortly."
    lead_id: uuid.UUID
