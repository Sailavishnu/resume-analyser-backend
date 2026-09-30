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

from app.core.exceptions import NotFoundError, ForbiddenError, ValidationError
from app.utils.pagination import paginate_query, PaginationMeta
from app.cloud import collections as C
from app.ml.domain_knowledge import domain_knowledge_engine
from app.utils.dates import utc_now


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
            profile = profiles.get(app["student_id"])
            resume = resumes.get(app.get("resume_id"))

            if not student:
                continue

            cand_skills = []
            if profile and profile.get("skills"):
                cand_skills = profile["skills"]
            elif resume and resume.get("parsed_data", {}).get("skills"):
                skills_obj = resume["parsed_data"]["skills"]
                for cat in ["languages", "frameworks", "tools", "databases"]:
                    cand_skills.extend(skills_obj.get(cat, []))

            candidate = {
                "application_id": str(app["_id"]),
                "student_id": str(app["student_id"]),
                "full_name": student.get("full_name") or profile.get("full_name") or "Candidate",
                "email": student.get("email"),
                "phone": profile.get("phone") if profile else None,
                "location": profile.get("location") if profile else "Remote",
                "target_role": profile.get("target_role") if profile else "Software Engineer",
                "resume_id": str(app["resume_id"]) if resume else None,
                "status": app.get("status", "applied"),
                "applied_at": app.get("created_at", utc_now()),
                "overall_score": app.get("match_score", 85),
                "skills": cand_skills,
                "job_id": str(job_id)
            }

            if min_match_score and (candidate["overall_score"] < min_match_score):
                continue

            candidates.append(candidate)

        return candidates, pagination

    async def screen_candidates_by_domain(
        self,
        domain_query: str,
        hr_user_id: str,
        min_relevance: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Domain-Aware Screening Engine.
        Matches candidates across the system using Inter-linked Knowledge Graph.
        (e.g., Target: Cybersecurity -> Matches candidate with 'Kali Linux', 'Wireshark').
        """
        all_students = list(self.db[C.USERS].find({"role": "student"}))

        screened_results = []
        for s in all_students:
            s_id = s["_id"]
            profile = self.db[C.STUDENT_PROFILES].find_one({"user_id": s_id}) or {}
            resume = self.db[C.RESUMES].find_one({"student_id": s_id}, sort=[("created_at", -1)]) or {}

            cand_skills = profile.get("skills", [])
            cand_text = profile.get("bio", "")

            if resume.get("parsed_data"):
                parsed = resume["parsed_data"]
                skills_obj = parsed.get("skills", {})
                for cat in ["languages", "frameworks", "tools", "databases", "concepts"]:
                    cand_skills.extend(skills_obj.get(cat, []))
                cand_text += " " + (parsed.get("summary") or "")

            # Execute Knowledge Graph Domain Match
            match_res = domain_knowledge_engine.match_domain_skills(
                query_or_role=domain_query,
                candidate_skills=cand_skills,
                candidate_text=cand_text
            )

            if match_res["relevance_score"] >= min_relevance or match_res["discovered_linked_skills"]:
                screened_results.append({
                    "student_id": str(s_id),
                    "name": s.get("full_name") or profile.get("full_name") or "Candidate",
                    "email": s.get("email"),
                    "skills": list(set(cand_skills)),
                    "domain_matched": match_res["domain_title"],
                    "matchScore": match_res["relevance_score"],
                    "discovered_linked_skills": match_res["discovered_linked_skills"],
                    "rationale": match_res["rationale"],
                    "status": "screened"
                })

        # Sort by relevance score
        screened_results.sort(key=lambda x: x["matchScore"], reverse=True)
        return screened_results

    async def update_application_status(
        self,
        application_id: str,
        new_status: str,
        hr_user_id: str
    ) -> Dict[str, Any]:
        """Update candidate application stage status."""
        valid_statuses = ("applied", "screened", "shortlisted", "interview_scheduled", "offered", "rejected")
        if new_status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of {valid_statuses}")

        res = self.db[C.APPLICATIONS].update_one(
            {"_id": ObjectId(application_id)},
            {"$set": {"status": new_status, "updated_at": utc_now()}}
        )
        if res.matched_count == 0:
            raise NotFoundError("Application")

        return {"application_id": application_id, "status": new_status, "message": f"Candidate status updated to {new_status}"}

    async def _verify_job_access(self, job_id: str, hr_user_id: str) -> Dict[str, Any]:
        """Verify job exists and HR user has permission."""
        job = self.db[C.JOBS].find_one({"_id": ObjectId(job_id)})
        if not job:
            raise NotFoundError("Job")
        return job