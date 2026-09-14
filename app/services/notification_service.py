"""
Notification service for managing user notifications.
"""
from bson import ObjectId
from pymongo.database import Database
from typing import Dict, Any, List

from app.core.exceptions import NotFoundError, ForbiddenError
from app.utils.dates import utc_now
from app.utils.pagination import paginate_query, PaginationMeta
from app.db import collections as C


class NotificationService:
    def __init__(self, db: Database):
        self.db = db
    
    async def get_user_notifications(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False
    ) -> tuple[List[Dict[str, Any]], PaginationMeta]:
        """Get notifications for user."""
        filter_dict = {"user_id": ObjectId(user_id)}
        
        if unread_only:
            filter_dict["is_read"] = False
        
        notifications, pagination = paginate_query(
            self.db[C.NOTIFICATIONS],
            filter_dict,
            page=page,
            page_size=page_size,
            sort_field="created_at",
            sort_direction=-1
        )
        
        for notif in notifications:
            notif["id"] = str(notif["_id"])
        
        return notifications, pagination
    
    async def mark_as_read(self, notification_id: str, user_id: str) -> Dict[str, Any]:
        """Mark notification as read."""
        notif = self.db[C.NOTIFICATIONS].find_one({"_id": ObjectId(notification_id)})
        if not notif:
            raise NotFoundError("Notification")
        
        if str(notif["user_id"]) != user_id:
            raise ForbiddenError("Cannot access this notification")
        
        self.db[C.NOTIFICATIONS].update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"is_read": True, "read_at": utc_now()}}
        )
        
        notif["is_read"] = True
        notif["id"] = str(notif["_id"])
        return notif
    
    async def mark_all_as_read(self, user_id: str) -> int:
        """Mark all notifications as read for user."""
        result = self.db[C.NOTIFICATIONS].update_many(
            {"user_id": ObjectId(user_id), "is_read": False},
            {"$set": {"is_read": True, "read_at": utc_now()}}
        )
        
        return result.modified_count
    
    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications."""
        return self.db[C.NOTIFICATIONS].count_documents({
            "user_id": ObjectId(user_id),
            "is_read": False
        })
    
    async def create_notification(
        self,
        user_id: str,
        type_: str,
        title: str,
        message: str,
        icon: str = "info",
        priority: str = "medium",
        action_url: str = None,
        related_entity_type: str = None,
        related_entity_id: str = None
    ) -> Dict[str, Any]:
        """Create new notification."""
        notification = {
            "user_id": ObjectId(user_id),
            "type": type_,
            "title": title,
            "message": message,
            "icon": icon,
            "action_url": action_url,
            "related_entity_type": related_entity_type,
            "related_entity_id": related_entity_id,
            "priority": priority,
            "is_read": False,
            "created_at": utc_now(),
        }
        
        result = self.db[C.NOTIFICATIONS].insert_one(notification)
        notification["_id"] = result.inserted_id
        notification["id"] = str(result.inserted_id)
        
        return notification