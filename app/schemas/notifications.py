from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NotificationOut(BaseModel):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    icon: str = "info"              # success | warning | info | alert
    action_url: Optional[str] = None
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None
    priority: str = "medium"        # high | medium | low
    is_read: bool = False
    created_at: Optional[datetime] = None


class NotificationUpdateRequest(BaseModel):
    is_read: bool = True