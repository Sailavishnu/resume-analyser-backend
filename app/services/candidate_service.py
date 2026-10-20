"""
Enhanced Candidate Management & HR Screening Service.

Supports:
1. Inter-Domain Knowledge Graph Screening (e.g. Kali Linux -> Cyber Security Specialist).
2. Candidate Stage Progression (Applied -> Screened -> Shortlisted -> Interview Scheduled -> Offered -> Rejected).
3. Mass candidate search across pool.
"""
from bson import ObjectId
from pymongo.database import Database
from typing import Dict, Any, List, Optional

from app.core.exceptions import NotFoundError, ForbiddenError
from app.utils.pagination import paginate_query, PaginationMeta
from app.cloud import collections as C


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
        await self._verify_job_access(job_id, hr_user_id)

        app_filter = {"job_id": ObjectId(job_id)}
        if status_filter:
            app_filter["status"] = status_filter
        else:
            app_filter["status"] = {"$ne": "hired"}

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

        student_ids = [app["student_id"] for app in applications]
        resume_ids = [app["resume_id"] for app in applications if app.get("resume_id")]

        students = {
            s["_id"]: s for s in self.db[C.USERS].find({"_id": {"$in": student_ids}})
        }
        profiles = {
            p["user_id"]: p for p in self.db[C.STUDENT_PROFILES].find({"user_id": {"$in": student_ids}})
        }
        resumes = {
            r["_id"]: r for r in self.db[C.RESUMES].find({"_id": {"$in": resume_ids}})
        }

        candidates = []
        for app in applications:
            student = students.get(app["student_id"])
            profile = profiles.get(app["student_id"]) or {}
            resume = resumes.get(app.get("resume_id"))

            if not student:
                continue

            cand_skills = []
            if profile and profile.get("skills"):
                cand_skills = profile["skills"]
            elif resume and (resume.get("parsed_data") or {}).get("skills"):
                skills_obj = (resume.get("parsed_data") or {})["skills"]
                for cat in ["languages", "frameworks", "tools", "databases"]:
                    cand_skills.extend(skills_obj.get(cat, []))

            candidate = {
                "application_id": str(app["_id"]),
                "student_id": str(app["student_id"]),
                "full_name": student.get("full_name") or profile.get("full_name") or "Candidate",
                "email": student.get("email"),
                "phone": profile.get("phone") if profile else None,
                "location": profile.get("location"),
                "target_role": profile.get("target_role"),
                "resume_id": str(app["resume_id"]) if resume else None,
                "status": app.get("status", "applied"),
                "applied_at": app.get("applied_at") or app.get("created_at"),
                "overall_score": app.get("match_score"),
                "skills": cand_skills,
                "job_id": str(job_id),
                "job_title": self.db[C.JOBS].find_one({"_id": ObjectId(job_id)}).get("title", "")
            }

            if min_match_score is not None and candidate["overall_score"] is not None and candidate["overall_score"] < min_match_score:
                continue

            candidates.append(candidate)

        return candidates, pagination

    async def _verify_job_access(self, job_id: str, hr_user_id: str) -> Dict[str, Any]:
        """Verify job exists and HR user has permission."""
        job = self.db[C.JOBS].find_one({"_id": ObjectId(job_id)})
        if not job:
            raise NotFoundError("Job")
        if str(job.get("created_by")) != hr_user_id:
            raise ForbiddenError("Not authorized to view this job's candidates")
        return job

    async def get_accepted_students(self, hr_user_id: str) -> List[Dict[str, Any]]:
        """Current students hired into jobs owned by this HR account."""
        jobs = list(self.db[C.JOBS].find({"created_by": ObjectId(hr_user_id)}, {"_id": 1, "title": 1}))
        if not jobs:
            return []
        job_map = {job["_id"]: job for job in jobs}
        apps = self.db[C.APPLICATIONS].find({"job_id": {"$in": list(job_map)}, "status": "hired"}).sort("updated_at", -1)
        results = []
        for app in apps:
            student = self.db[C.USERS].find_one({"_id": app["student_id"], "is_active": {"$ne": False}}) or {}
            if not student:
                continue
            profile = self.db[C.STUDENT_PROFILES].find_one({"user_id": app["student_id"]}) or {}
            results.append({
                "student_id": str(app["student_id"]), "full_name": student.get("full_name") or "Student",
                "email": student.get("email", ""), "phone": profile.get("phone"),
                "location": profile.get("location"), "target_role": profile.get("target_role"),
                "job_id": str(app["job_id"]), "job_title": job_map[app["job_id"]].get("title", ""),
                "accepted_at": app.get("updated_at")
            })
        return results
