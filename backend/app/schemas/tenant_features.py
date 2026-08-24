from pydantic import BaseModel, Field


class TenantFeaturePolicyEntry(BaseModel):
    tenant_editable: bool = False


class TenantFeaturesResponse(BaseModel):
    qa_dashboard: bool = True
    compatibility_center: bool = True
    governance_sandbox: bool = True
    reports: bool = True
    developer_portal: bool = True


class TenantFeaturePolicyResponse(BaseModel):
    qa_dashboard: TenantFeaturePolicyEntry = Field(default_factory=TenantFeaturePolicyEntry)
    compatibility_center: TenantFeaturePolicyEntry = Field(default_factory=TenantFeaturePolicyEntry)
    governance_sandbox: TenantFeaturePolicyEntry = Field(default_factory=TenantFeaturePolicyEntry)
    reports: TenantFeaturePolicyEntry = Field(default_factory=TenantFeaturePolicyEntry)
    developer_portal: TenantFeaturePolicyEntry = Field(default_factory=TenantFeaturePolicyEntry)
