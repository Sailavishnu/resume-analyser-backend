"""
Notifications API routes.
"""
from fastapi import APIRouter, Depends, Query
from pymongo.database import Database
from typing import Optional

from app.core.dependencies import get_current_user
from app.db.mongodb import get_database
from app.schemas.common import DataResponse, PaginatedResponse, MessageResponse
from app.schemas.notifications import NotificationOut, NotificationUpdateRequest
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=PaginatedResponse[NotificationOut])
async def get_my_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: Optional[bool] = Query(False),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database)
):
    """Get notifications for authenticated user."""
    notification_service = NotificationService(db)
    
    notifications, pagination = await notification_service.get_user_notifications(
        user_id=current_user["id"],
        page=page,
        page_size=page_size,
        unread_only=unread_only
    )
    
    return PaginatedResponse(
        data=[NotificationOut(**notif) for notif in notifications],
        pagination=pagination
    )


@router.get("/unread-count", response_model=DataResponse[dict])
async def get_unread_count(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database)
):
    """Get count of unread notifications."""
    notification_service = NotificationService(db)
    
    count = await notification_service.get_unread_count(current_user["id"])
    
    return DataResponse(data={"unread_count": count})


@router.patch("/{notification_id}/read", response_model=DataResponse[NotificationOut])
async def mark_notification_as_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database)
):
    """Mark notification as read."""
    notification_service = NotificationService(db)
    
    notification = await notification_service.mark_as_read(notification_id, current_user["id"])
    
    return DataResponse(data=NotificationOut(**notification))


@router.post("/read-all", response_model=MessageResponse)
async def mark_all_as_read(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_database)
):
    """Mark all notifications as read."""
    notification_service = NotificationService(db)
    
    count = await notification_service.mark_all_as_read(current_user["id"])
    
    return MessageResponse(message=f"Marked {count} notifications as read")