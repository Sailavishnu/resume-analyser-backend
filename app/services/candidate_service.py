"""
Candidate management service for HR users.
"""
from bson import ObjectId
from pymongo.database import Database
from typing import Dict, Any, List, Optional

from app.core.exceptions import NotFoundError, ForbiddenError
from app.utils.pagination import paginate_query, PaginationMeta
from app.db import collections as C


class CandidateService:
    def __init__(self, db: Database):
        self.db = db
    
    async def get_job_candidates(
        self,
        job_id: str,
        hr_user_id: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[str] = None,
        min_match_score: Optional[int] = None
    ) -> tuple[List[Dict[str, Any]], PaginationMeta]:
        """Get candidates who applied to a specific job."""
        
        # Verify HR can access this job
        job = await self._verify_job_access(job_id, hr_user_id)
        
        # Build application filter
        app_filter = {"job_id": ObjectId(job_id)}
        if status_filter:
            app_filter["status"] = status_filter
        
        # Get applications with pagination
        applications, pagination = paginate_query(
            self.db[C.APPLICATIONS],
            app_filter,
            page=page,
            page_size=page_size,
            sort_field="applied_at",
            sort_direction=-1
        )
        
        if not applications:
            return [], pagination
        
        # Get student and resume data
        student_ids = [app["student_id"] for app in applications]
        resume_ids = [app["resume_id"] for app in applications]
        
        # Fetch students
        students = {
            student["_id"]: student
            for student in self.db[C.USERS].find({
                "_id": {"$in": student_ids},
                "role": "student"
            })
        }
        
        # Fetch student profiles
        profiles = {
            profile["user_id"]: profile
            for profile in self.db[C.STUDENT_PROFILES].find({
                "user_id": {"$in": student_ids}
            })
        }
        
        # Fetch resumes
        resumes = {
            resume["_id"]: resume
            for resume in self.db[C.RESUMES].find({
                "_id": {"$in": resume_ids}
            })
        }
        
        # Fetch match scores
        matches = {
            match["resume_id"]: match
            for match in self.db[C.JOB_MATCHES].find({
                "job_id": ObjectId(job_id),
                "resume_id": {"$in": resume_ids}
            })
        }
        
        # Build candidate objects
        candidates = []
        for app in applications:
            student = students.get(app["student_id"])
            profile = profiles.get(app["student_id"])
            resume = resumes.get(app["resume_id"])
            match = matches.get(app["resume_id"])
            
            if not student:
                continue  # Skip if student not found
            
            candidate = {
                "application_id": str(app["_id"]),
                "student_id": str(app["student_id"]),
                "full_name": student.get("full_name"),
                "email": student.get("email"),
                "location": profile.get("location") if profile else None,
                "target_role": profile.get("target_role") if profile else None,
                "resume_id": str(app["resume_id"]) if resume else None,
                "resume_url": resume.get("cloudinary_secure_url") if resume else None,
                "status": app["status"],
                "applied_at": app["applied_at"],
                "overall_score": int(match["overall_score"]) if match else None,
                "ats_score": None,  # Would come from resume analysis
                "skills_score": None,
                "matched_skills": match.get("matched_skills", []) if match else [],
                "missing_skills": match.get("missing_skills", []) if match else [],
                "job_id": str(job_id),
                "job_title": job["title"]
            }
            
            # Apply match score filter
            if min_match_score and (not candidate["overall_score"] or candidate["overall_score"] < min_match_score):
                continue
            
            candidates.append(candidate)
        
        # Update pagination total if filtered by score
        if min_match_score:
            pagination.total = len(candidates)
            pagination.total_pages = (len(candidates) + page_size - 1) // page_size
        
        return candidates, pagination
    
    async def get_candidate_details(
        self,
        application_id: str,
        hr_user_id: str
    ) -> Dict[str, Any]:
        """Get detailed candidate information."""
        
        # Get application
        app = self.db[C.APPLICATIONS].find_one({"_id": ObjectId(application_id)})
        if not app:
            raise NotFoundError("Application")
        
        # Verify HR can access this application
        await self._verify_job_access(str(app["job_id"]), hr_user_id)
        
        # Get student details
        student = self.db[C.USERS].find_one({"_id": app["student_id"]})
        profile = self.db[C.STUDENT_PROFILES].find_one({"user_id": app["student_id"]})
        resume = self.db[C.RESUMES].find_one({"_id": app["resume_id"]})
        
        if not student:
            raise NotFoundError("Student")
        
        # Get match details
        match = self.db[C.JOB_MATCHES].find_one({
            "job_id": app["job_id"],
            "resume_id": app["resume_id"]
        })
        
        # Get resume analysis
        analysis = self.db[C.RESUME_ANALYSES].find_one({
            "resume_id": app["resume_id"]
        }, sort=[("created_at", -1)])
        
        candidate = {
            "application_id": str(app["_id"]),
            "student_id": str(app["student_id"]),
            "full_name": student["full_name"],
            "email": student["email"],
            "phone": profile.get("phone") if profile else None,
            "location": profile.get("location") if profile else None,
            "target_role": profile.get("target_role") if profile else None,
            "bio": profile.get("bio") if profile else None,
            "preferred_work_mode": profile.get("preferred_work_mode") if profile else None,
            
            # Resume details
            "resume_id": str(app["resume_id"]) if resume else None,
            "resume_url": resume.get("cloudinary_secure_url") if resume else None,
            "resume_name": resume.get("name") if resume else None,
            
            # Application details
            "status": app["status"],
            "applied_at": app["applied_at"],
            "updated_at": app["updated_at"],
            
            # Match analysis
            "overall_score": int(match["overall_score"]) if match else None,
            "match_features": match.get("features") if match else None,
            "matched_skills": match.get("matched_skills", []) if match else [],
            "missing_skills": match.get("missing_skills", []) if match else [],
            "recommendations": match.get("recommendations", []) if match else [],
            
            # Resume analysis
            "resume_health_score": analysis.get("overall_score") if analysis else None,
            "ats_score": analysis.get("ats_score") if analysis else None,
            "section_scores": analysis.get("section_scores") if analysis else None,
        }
        
        # Add parsed resume data if available
        if resume and resume.get("parsed_data"):
            parsed = resume["parsed_data"]
            candidate.update({
                "summary": parsed.get("summary"),
                "skills": parsed.get("skills"),
                "experience": parsed.get("experience", []),
                "projects": parsed.get("projects", []),
                "education": parsed.get("education", []),
            })
        
        return candidate
    
    async def _verify_job_access(self, job_id: str, hr_user_id: str) -> Dict[str, Any]:
        """Verify HR user can access candidates for this job."""
        job = self.db[C.JOBS].find_one({"_id": ObjectId(job_id)})
        if not job:
            raise NotFoundError("Job")
        
        hr_profile = self.db[C.RECRUITER_PROFILES].find_one({"user_id": ObjectId(hr_user_id)})
        if not hr_profile:
            raise ForbiddenError("HR profile required")
        
        if job.get("company_id") != hr_profile.get("company_id"):
            raise ForbiddenError("Can only access candidates for your company's jobs")
        
        return job