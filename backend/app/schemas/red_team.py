from pydantic import BaseModel, Field


class RedTeamCase(BaseModel):
    case_id: str
    category: str
    name: str
    prompt: str
    expected_detection: bool = True


class RedTeamCaseResult(RedTeamCase):
    detected: bool
    recommended_action: str
    highest_severity: str
    passed: bool
    matched_rules: list[str] = Field(default_factory=list)


class RedTeamCampaignResponse(BaseModel):
    campaign_id: str
    campaign_name: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    detection_rate: float
    overall_status: str
    results: list[RedTeamCaseResult]