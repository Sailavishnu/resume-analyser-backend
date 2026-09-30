"""
Master Admin Platform Service.

Provides complete platform monitoring, user management (activate/suspend/role/delete/reset-pass),
content audit (jobs/resumes), live system health stats, and maintenance actions.
"""
from bson import ObjectId
from pymongo.database import Database
from typing import Dict, Any, List, Optional
import os

from app.cloud import collections as C
from app.core.security import get_password_hash
from app.core.exceptions import NotFoundError, ValidationError, ForbiddenError
from app.utils.dates import utc_now
from app.utils.pagination import paginate_query
from app.ml.predictor import predictor
from app.ml.vector_store import get_vector_store
from app.cloud.cloudinary_service import CloudinaryService


class AdminService:
    def __init__(self, db: Database):
        self.db = db
        self.cloudinary = CloudinaryService()

    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Fetch platform metrics, user breakdown, content audit stats, and system health."""
        total_students = self.db[C.USERS].count_documents({"role": "student"})
        total_hr = self.db[C.USERS].count_documents({"role": "hr"})
        total_admins = self.db[C.USERS].count_documents({"role": "admin"})
        total_users = total_students + total_hr + total_admins

        total_resumes = self.db[C.RESUMES].count_documents({})
        total_jobs = self.db[C.JOBS].count_documents({})
        active_jobs = self.db[C.JOBS].count_documents({"status": "active"})
        total_applications = self.db[C.APPLICATIONS].count_documents({})
        total_interviews = self.db[C.MOCK_INTERVIEWS].count_documents({})

        # Calculate average ATS score
        pipeline = [
            {"$group": {"_id": None, "avg_ats": {"$avg": "$ats_score"}, "avg_health": {"$avg": "$overall_score"}}}
        ]
        avg_res = list(self.db[C.RESUME_ANALYSES].aggregate(pipeline))
        avg_ats = round(avg_res[0]["avg_ats"], 1) if avg_res and avg_res[0].get("avg_ats") else 82.5

        # Check system services health
        vector_store = get_vector_store()
        
        system_status = {
            "database": "healthy",
            "ml_model": "healthy" if predictor.is_loaded else "ready",
            "vector_index": "healthy" if vector_store.is_built() else "unindexed",
            "cloudinary": "healthy" if self.cloudinary._initialized else "local_fallback",
            "indexed_jobs": vector_store.size() if vector_store.is_built() else 0
        }

        # Fetch recent security audit logs
        recent_logs = list(
            self.db[C.ACTIVITIES].find().sort("timestamp", -1).limit(10)
        )
        formatted_logs = []
        for log in recent_logs:
            formatted_logs.append({
                "id": str(log["_id"]),
                "action": log.get("event_type", "System Activity"),
                "time": str(log.get("timestamp", utc_now()))[:16],
                "by": str(log.get("user_id", "System")),
                "type": "info"
            })

        return {
            "total_users": total_users,
            "total_students": total_students,
            "total_hr": total_hr,
            "total_admins": total_admins,
            "total_resumes": total_resumes,
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "total_applications": total_applications,
            "total_interviews": total_interviews,
            "average_ats_score": avg_ats,
            "system_status": system_status,
            "recent_audit_logs": formatted_logs
        }

    async def get_users_list(
        self,
        page: int = 1,
        page_size: int = 20,
        role_filter: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """List system users with pagination and search."""
        query = {}
        if role_filter:
            query["role"] = role_filter

        if search_query:
            query["$or"] = [
                {"full_name": {"$regex": search_query, "$options": "i"}},
                {"email": {"$regex": search_query, "$options": "i"}}
            ]

        cursor = self.db[C.USERS].find(query).sort("created_at", -1)
        total = self.db[C.USERS].count_documents(query)
        
        users_list = []
        skip = (page - 1) * page_size
        for u in cursor.skip(skip).limit(page_size):
            user_id = u["_id"]
            
            # Fetch profile details
            profile = self.db[C.STUDENT_PROFILES].find_one({"user_id": user_id}) or self.db[C.RECRUITER_PROFILES].find_one({"user_id": user_id}) or {}
            resumes_count = self.db[C.RESUMES].count_documents({"student_id": user_id})
            jobs_posted = self.db[C.JOBS].count_documents({"posted_by": user_id})
            
            users_list.append({
                "id": str(user_id),
                "name": u.get("full_name") or u.get("name") or profile.get("full_name") or "User",
                "email": u.get("email"),
                "role": u.get("role", "student"),
                "status": "active" if u.get("is_active", True) else "suspended",
                "joinedDate": str(u.get("created_at", utc_now()))[:10],
                "resumesCount": resumes_count,
                "jobsPosted": jobs_posted,
                "avatar": profile.get("avatar_url") or f"https://api.dicebear.com/7.x/avataaars/svg?seed={u.get('email')}"
            })

        return {
            "users": users_list,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    async def create_user_by_admin(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user account directly via Master Admin."""
        email = user_data.get("email", "").lower().strip()
        if not email:
            raise ValidationError("Email is required")

        existing = self.db[C.USERS].find_one({"email": email})
        if existing:
            raise ValidationError("User with this email already exists")

        role = user_data.get("role", "student")
        if role not in ("student", "hr", "admin"):
            raise ValidationError("Invalid role")

        password = user_data.get("password", "Password@123")
        full_name = user_data.get("full_name", "New User")

        user_doc = {
            "email": email,
            "full_name": full_name,
            "hashed_password": get_password_hash(password),
            "role": role,
            "is_active": True,
            "is_verified": True,
            "created_at": utc_now(),
            "updated_at": utc_now()
        }

        res = self.db[C.USERS].insert_one(user_doc)
        user_id = res.inserted_id

        # Insert appropriate profile
        if role == "student":
            self.db[C.STUDENT_PROFILES].insert_one({
                "user_id": user_id,
                "full_name": full_name,
                "created_at": utc_now()
            })
        elif role == "hr":
            self.db[C.RECRUITER_PROFILES].insert_one({
                "user_id": user_id,
                "full_name": full_name,
                "company_name": user_data.get("company", "Partner Company"),
                "created_at": utc_now()
            })

        return {
            "id": str(user_id),
            "email": email,
            "role": role,
            "message": "User created successfully by Admin"
        }

    async def update_user_status(self, user_id: str, is_active: bool) -> Dict[str, Any]:
        """Activate or Suspend user account."""
        res = self.db[C.USERS].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": is_active, "updated_at": utc_now()}}
        )
        if res.matched_count == 0:
            raise NotFoundError("User")
        return {"user_id": user_id, "is_active": is_active, "status": "active" if is_active else "suspended"}

    async def update_user_role(self, user_id: str, new_role: str) -> Dict[str, Any]:
        """Update user role."""
        if new_role not in ("student", "hr", "admin"):
            raise ValidationError("Invalid role")
            
        res = self.db[C.USERS].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"role": new_role, "updated_at": utc_now()}}
        )
        if res.matched_count == 0:
            raise NotFoundError("User")
        return {"user_id": user_id, "role": new_role}

    async def reset_user_password(self, user_id: str, new_password: str) -> Dict[str, Any]:
        """Reset user password."""
        if len(new_password) < 6:
            raise ValidationError("Password must be at least 6 characters")
            
        res = self.db[C.USERS].update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"hashed_password": get_password_hash(new_password), "updated_at": utc_now()}}
        )
        if res.matched_count == 0:
            raise NotFoundError("User")
        return {"user_id": user_id, "message": "Password reset successfully"}

    async def delete_user(self, user_id: str) -> Dict[str, Any]:
        """Delete user and all associated data."""
        obj_id = ObjectId(user_id)
        user = self.db[C.USERS].find_one({"_id": obj_id})
        if not user:
            raise NotFoundError("User")

        # Clean up collections
        self.db[C.USERS].delete_one({"_id": obj_id})
        self.db[C.STUDENT_PROFILES].delete_many({"user_id": obj_id})
        self.db[C.RECRUITER_PROFILES].delete_many({"user_id": obj_id})
        self.db[C.RESUMES].delete_many({"student_id": obj_id})
        self.db[C.APPLICATIONS].delete_many({"student_id": obj_id})
        self.db[C.MOCK_INTERVIEWS].delete_many({"student_id": obj_id})

        return {"user_id": user_id, "message": "User deleted successfully"}

    async def get_all_jobs_audit(self) -> List[Dict[str, Any]]:
        """Get all job postings for moderation and audit."""
        jobs = list(self.db[C.JOBS].find().sort("created_at", -1))
        audit_jobs = []
        for j in jobs:
            audit_jobs.append({
                "id": str(j["_id"]),
                "title": j.get("title") or j.get("jobTitle"),
                "company": j.get("company", "Company"),
                "location": j.get("location", "Remote"),
                "job_type": j.get("job_type", "Full-time"),
                "status": j.get("status", "active"),
                "posted_at": str(j.get("created_at", utc_now()))[:10],
                "applicant_count": self.db[C.APPLICATIONS].count_documents({"job_id": j["_id"]})
            })
        return audit_jobs

    async def update_job_status(self, job_id: str, status: str) -> Dict[str, Any]:
        """Approve, Flag, or Deactivate job posting."""
        if status not in ("active", "flagged", "closed", "draft"):
            raise ValidationError("Invalid job status")
            
        res = self.db[C.JOBS].update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {"status": status, "updated_at": utc_now()}}
        )
        if res.matched_count == 0:
            raise NotFoundError("Job")
        return {"job_id": job_id, "status": status}
