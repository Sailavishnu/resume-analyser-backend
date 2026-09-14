"""
Job application service - apply, track, manage pipeline.
"""
from bson import ObjectId
from pymongo.database import Database
from typing import Dict, Any, List

from app.core.exceptions import NotFoundError, ConflictError, ForbiddenError, ValidationError
from app.utils.dates import utc_now
from app.utils.pagination import paginate_query, PaginationMeta
from app.db import collections as C


class ApplicationService:
    def __init__(self, db: Database):
        self.db = db
    
    async def apply_to_job(self, student_id: str, job_id: str, resume_id: str) -> Dict[str, Any]:
        """Submit job application."""
        # Verify job exists and is active
        job = self.db[C.JOBS].find_one({"_id": ObjectId(job_id)})
        if not job:
            raise NotFoundError("Job")
        
        if job["status"] != "active":
            raise ValidationError("Job is not currently accepting applications")
        
        # Verify resume belongs to student
        resume = self.db[C.RESUMES].find_one({
            "_id": ObjectId(resume_id),
            "student_id": ObjectId(student_id)
        })
        if not resume:
            raise NotFoundError("Resume not found or access denied")
        
        # Check for duplicate application
        existing = self.db[C.APPLICATIONS].find_one({
            "student_id": ObjectId(student_id),
            "job_id": ObjectId(job_id)
        })
        if existing:
            raise ConflictError("Already applied to this job")
        
        # Create application
        app_doc = {
            "student_id": ObjectId(student_id),
            "job_id": ObjectId(job_id),
            "resume_id": ObjectId(resume_id),
            "status": "applied",
            "applied_at": utc_now(),
            "updated_at": utc_now(),
        }
        
        result = self.db[C.APPLICATIONS].insert_one(app_doc)
        app_id = result.inserted_id
        
        # Create initial timeline event
        self.db[C.APPLICATION_EVENTS].insert_one({
            "application_id": app_id,
            "event_type": "applied",
            "message": "Application submitted",
            "created_at": utc_now(),
        })
        
        # Update job applicant count
        self.db[C.JOBS].update_one(
            {"_id": ObjectId(job_id)},
            {"$inc": {"applicant_count": 1}}
        )
        
        # Create notification for student
        await self._create_notification(
            student_id,
            "application_submitted",
            f"Application submitted for '{job['title']}'",
            f"Your application has been successfully submitted.",
            f"/applications/{app_id}"
        )
        
        app_doc["_id"] = app_id
        app_doc["id"] = str(app_id)
        return app_doc
    
    async def get_student_applications(
        self,
        student_id: str,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Dict[str, Any]], PaginationMeta]:
        """Get applications for a student."""
        filter_dict = {"student_id": ObjectId(student_id)}
        
        applications, pagination = paginate_query(
            self.db[C.APPLICATIONS],
            filter_dict,
            page=page,
            page_size=page_size,
            sort_field="applied_at",
            sort_direction=-1
        )
        
        # Enrich with job and company details
        job_ids = [app["job_id"] for app in applications]
        jobs = {
            job["_id"]: job
            for job in self.db[C.JOBS].find({"_id": {"$in": job_ids}})
        }
        
        company_ids = [job.get("company_id") for job in jobs.values() if job.get("company_id")]
        companies = {
            company["_id"]: company
            for company in self.db[C.COMPANIES].find({"_id": {"$in": company_ids}})
        }
        
        for app in applications:
            app["id"] = str(app["_id"])
            job = jobs.get(app["job_id"])
            if job:
                app["job_title"] = job.get("title")
                company = companies.get(job.get("company_id"))
                if company:
                    app["company_name"] = company.get("name")
                    app["company_logo"] = company.get("logo_url")
        
        return applications, pagination
    
    async def get_application_by_id(self, app_id: str, user_id: str = None) -> Dict[str, Any]:
        """Get application by ID with access control."""
        app = self.db[C.APPLICATIONS].find_one({"_id": ObjectId(app_id)})
        if not app:
            raise NotFoundError("Application")
        
        # Verify access if user_id provided
        if user_id:
            # Check if student owns application
            if str(app["student_id"]) == user_id:
                pass  # Student can access own application
            else:
                # Check if HR can access (same company as job)
                hr_profile = self.db[C.RECRUITER_PROFILES].find_one({"user_id": ObjectId(user_id)})
                if hr_profile:
                    job = self.db[C.JOBS].find_one({"_id": app["job_id"]})
                    if not job or job.get("company_id") != hr_profile.get("company_id"):
                        raise ForbiddenError("Access denied")
                else:
                    raise ForbiddenError("Access denied")
        
        app["id"] = str(app["_id"])
        return app
    
    async def update_application_status(
        self,
        app_id: str,
        new_status: str,
        hr_user_id: str,
        reason: str = None
    ) -> Dict[str, Any]:
        """Update application status (HR only)."""
        app = await self.get_application_by_id(app_id)
        
        # Verify HR can update this application
        hr_profile = self.db[C.RECRUITER_PROFILES].find_one({"user_id": ObjectId(hr_user_id)})
        if not hr_profile:
            raise ForbiddenError("HR profile required")
        
        job = self.db[C.JOBS].find_one({"_id": app["job_id"]})
        if not job or job.get("company_id") != hr_profile.get("company_id"):
            raise ForbiddenError("Can only update applications for your company's jobs")
        
        # Validate status transition
        valid_statuses = ["applied", "under_review", "shortlisted", "interview", "offer", "hired", "rejected", "withdrawn"]
        if new_status not in valid_statuses:
            raise ValidationError(f"Invalid status: {new_status}")
        
        # Update application
        self.db[C.APPLICATIONS].update_one(
            {"_id": ObjectId(app_id)},
            {"$set": {"status": new_status, "updated_at": utc_now()}}
        )
        
        # Create timeline event
        message = f"Application status changed to {new_status}"
        if reason:
            message += f": {reason}"
        
        self.db[C.APPLICATION_EVENTS].insert_one({
            "application_id": ObjectId(app_id),
            "event_type": "status_changed",
            "message": message,
            "created_by": ObjectId(hr_user_id),
            "created_at": utc_now(),
        })
        
        # Create notification for student
        await self._create_notification(
            str(app["student_id"]),
            "application_status_changed",
            f"Application Status Update - {job['title']}",
            f"Your application status has been updated to: {new_status}",
            f"/applications/{app_id}"
        )
        
        return await self.get_application_by_id(app_id)
    
    async def withdraw_application(self, app_id: str, student_id: str) -> Dict[str, Any]:
        """Withdraw application (student only)."""
        app = await self.get_application_by_id(app_id, student_id)
        
        if app["status"] in ["hired", "rejected", "withdrawn"]:
            raise ValidationError("Cannot withdraw application in current status")
        
        # Update status
        self.db[C.APPLICATIONS].update_one(
            {"_id": ObjectId(app_id)},
            {"$set": {"status": "withdrawn", "updated_at": utc_now()}}
        )
        
        # Create timeline event
        self.db[C.APPLICATION_EVENTS].insert_one({
            "application_id": ObjectId(app_id),
            "event_type": "withdrawn",
            "message": "Application withdrawn by candidate",
            "created_at": utc_now(),
        })
        
        return await self.get_application_by_id(app_id)
    
    async def get_application_timeline(self, app_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get application timeline events."""
        # Verify access
        await self.get_application_by_id(app_id, user_id)
        
        cursor = self.db[C.APPLICATION_EVENTS].find(
            {"application_id": ObjectId(app_id)}
        ).sort("created_at", 1)
        
        events = []
        for event in cursor:
            event["id"] = str(event["_id"])
            events.append(event)
        
        return events
    
    async def add_application_note(
        self,
        app_id: str,
        student_id: str,
        content: str
    ) -> Dict[str, Any]:
        """Add private note to application (student only)."""
        # Verify student owns application
        await self.get_application_by_id(app_id, student_id)
        
        note_doc = {
            "application_id": ObjectId(app_id),
            "student_id": ObjectId(student_id),
            "content": content,
            "created_at": utc_now(),
        }
        
        result = self.db[C.APPLICATION_NOTES].insert_one(note_doc)
        note_doc["_id"] = result.inserted_id
        note_doc["id"] = str(result.inserted_id)
        
        return note_doc
    
    async def get_application_notes(self, app_id: str, student_id: str) -> List[Dict[str, Any]]:
        """Get private notes for application."""
        # Verify access
        await self.get_application_by_id(app_id, student_id)
        
        cursor = self.db[C.APPLICATION_NOTES].find({
            "application_id": ObjectId(app_id),
            "student_id": ObjectId(student_id)
        }).sort("created_at", -1)
        
        notes = []
        for note in cursor:
            note["id"] = str(note["_id"])
            notes.append(note)
        
        return notes
    
    # ─── Private methods ───────────────────────────────────────────────────
    
    async def _create_notification(
        self,
        user_id: str,
        type_: str,
        title: str,
        message: str,
        action_url: str = None
    ) -> None:
        """Create notification for user."""
        notification = {
            "user_id": ObjectId(user_id),
            "type": type_,
            "title": title,
            "message": message,
            "icon": "info",
            "action_url": action_url,
            "priority": "medium",
            "is_read": False,
            "created_at": utc_now(),
        }
        
        self.db[C.NOTIFICATIONS].insert_one(notification)