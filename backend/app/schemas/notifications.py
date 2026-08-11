from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    severity: str
    category: str
    timestamp: str
    action: str
    resource: str
    status: str


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int
