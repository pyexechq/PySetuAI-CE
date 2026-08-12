from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoutingGroupMember(BaseModel):
    model: str = Field(..., description="Target model or provider name")
    weight: float = Field(default=100.0, description="Routing weight / ratio percentage")
    priority: int = Field(default=1, description="Fallback priority order (lower = higher priority)")

    model_config = ConfigDict(from_attributes=True)


class RoutingGroupCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: str = Field(default="")
    strategy: str = Field(default="weighted", max_length=50)
    members: list[RoutingGroupMember] = Field(default_factory=list)
    status: str = Field(default="active", max_length=20)


class RoutingGroupUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    strategy: str | None = Field(default=None, max_length=50)
    members: list[RoutingGroupMember] | None = None
    status: str | None = Field(default=None, max_length=20)


class RoutingGroupResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: str
    strategy: str
    members: list[RoutingGroupMember]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
