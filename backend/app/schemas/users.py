from pydantic import BaseModel, EmailStr, Field


class TenantUserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool


class TenantUserCreateRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = "developer"


class TenantUserUpdateRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class RbacPermissionsResponse(BaseModel):
    role: str
    permissions: list[str]


class RbacMatrixResponse(BaseModel):
    permissions: list[str]
    roles: list[str]
    matrix: dict[str, dict[str, bool]]
