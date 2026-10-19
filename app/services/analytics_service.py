"""Analytics for student, recruiter, and platform activity."""

from bson import ObjectId

from app.cloud import collections as C


class AnalyticsService:
    """Build analytics from the platform's existing MongoDB collections."""

    def __init__(self, db):
        self.db = db

    @staticmethod
    def _count(collection, query=None):
        return collection.count_documents(query or {})

    async def get_student_analytics(self, student_id: str) -> dict:
        user_id = ObjectId(student_id)
        profile = self.db[C.STUDENT_PROFILES].find_one({"user_id": user_id}) or {}
        applications = list(self.db[C.APPLICATIONS].find({"student_id": user_id}, {"status": 1}))
        breakdown = {
            "applied": 0, "under_review": 0, "shortlisted": 0, "interview": 0,
            "offer": 0, "hired": 0, "rejected": 0, "withdrawn": 0,
        }
        for application in applications:
            status = application.get("status", "applied")
            if status in breakdown:
                breakdown[status] += 1

        resumes = list(self.db[C.RESUMES].find({"student_id": user_id}, {"_id": 1}))
        resume_ids = [resume["_id"] for resume in resumes]
        latest_analysis = self.db[C.RESUME_ANALYSES].find_one(
            {"resume_id": {"$in": resume_ids}}, sort=[("created_at", -1)]
        ) if resume_ids else None
        interview_count = self._count(self.db[C.INTERVIEWS], {"student_id": user_id})
        assessment_count = self._count(self.db[C.ASSESSMENT_ATTEMPTS], {"student_id": user_id})
        roadmap = self.db[C.ROADMAPS].find_one({"student_id": user_id}) or {}
        history = list(self.db[C.CAREER_READINESS_HISTORY].find(
            {"student_id": user_id}, {"_id": 0, "date": 1, "score": 1}
        ).sort("date", 1).limit(90))
        for point in history:
            if point.get("date") is not None and not isinstance(point["date"], str):
                point["date"] = point["date"].isoformat()

        return {
            "student_id": student_id,
            "career_readiness_score": int(profile.get("career_readiness_score", 0) or 0),
            "resume_health_score": (latest_analysis or {}).get("overall_score"),
            "ats_score": (latest_analysis or {}).get("ats_score"),
            "current_streak": int(profile.get("current_streak", 0) or 0),
            "longest_streak": int(profile.get("longest_streak", 0) or 0),
            "total_applications": len(applications),
            "total_interviews": interview_count,
            "total_assessments": assessment_count,
            "roadmap_progress": int(roadmap.get("progress", roadmap.get("progress_percentage", 0)) or 0),
            "career_history": history,
            "application_breakdown": breakdown,
        }

    async def get_hr_analytics(self, recruiter_id: str) -> dict:
        recruiter_oid = ObjectId(recruiter_id)
        profile = self.db[C.RECRUITER_PROFILES].find_one({"user_id": recruiter_oid}) or {}
        company_id = profile.get("company_id")
        jobs = list(self.db[C.JOBS].find({"company_id": company_id})) if company_id else []
        job_ids = [job["_id"] for job in jobs]
        applications = list(self.db[C.APPLICATIONS].find(
            {"job_id": {"$in": job_ids}}, {"job_id": 1, "status": 1, "match_score": 1}
        )) if job_ids else []
        status_counts = {status: 0 for status in ("shortlisted", "interview", "offer", "hired")}
        by_job = {str(job["_id"]): [] for job in jobs}
        for application in applications:
            status = application.get("status", "applied")
            if status in status_counts:
                status_counts[status] += 1
            by_job.setdefault(str(application["job_id"]), []).append(application)

        stages = [status_counts["shortlisted"], status_counts["interview"], status_counts["offer"], status_counts["hired"]]
        previous = [len(applications), *stages[:-1]]
        rates = [round((current / total) * 100, 2) if total else 0.0 for current, total in zip(stages, previous)]
        scores = [app["match_score"] for app in applications if isinstance(app.get("match_score"), (int, float))]
        job_metrics = []
        for job in jobs:
            job_apps = by_job.get(str(job["_id"]), [])
            counts = {status: sum(1 for app in job_apps if app.get("status") == status)
                      for status in ("shortlisted", "interview", "offer", "hired")}
            job_scores = [app["match_score"] for app in job_apps if isinstance(app.get("match_score"), (int, float))]
            job_metrics.append({
                "job_id": str(job["_id"]), "job_title": job.get("title", ""),
                "total_applicants": len(job_apps), "shortlisted": counts["shortlisted"],
                "interviewed": counts["interview"], "offered": counts["offer"], "hired": counts["hired"],
                "avg_match_score": sum(job_scores) / len(job_scores) if job_scores else None,
            })

        return {
            "recruiter_id": recruiter_id,
            "company_id": str(company_id) if company_id else "",
            "active_jobs": sum(job.get("status") == "active" for job in jobs),
            "total_applicants": len(applications),
            "total_shortlisted": status_counts["shortlisted"],
            "total_interviewed": status_counts["interview"],
            "total_hired": status_counts["hired"],
            "avg_match_score": sum(scores) / len(scores) if scores else None,
            "pipeline_metrics": dict(zip(("applied_to_shortlisted", "shortlisted_to_interviewed", "interviewed_to_offered", "offered_to_hired"), rates)),
            "job_metrics": job_metrics,
            "top_skills": [],
        }

    async def get_admin_analytics(self) -> dict:
        users = list(self.db[C.USERS].find({}, {"role": 1, "created_at": 1}))
        students = sum(user.get("role") == "student" for user in users)
        recruiters = sum(user.get("role") in ("hr", "recruiter") for user in users)
        analyses = self._count(self.db[C.RESUME_ANALYSES])
        return {
            "total_users": len(users), "total_students": students, "total_recruiters": recruiters,
            "total_companies": self._count(self.db[C.COMPANIES]),
            "total_jobs": self._count(self.db[C.JOBS]),
            "total_applications": self._count(self.db[C.APPLICATIONS]),
            "total_resumes": self._count(self.db[C.RESUMES]),
            "total_analyses": analyses,
            "active_jobs": self._count(self.db[C.JOBS], {"status": "active"}),
            "user_growth": [], "feature_usage": [],
        }

    async def get_ml_analytics(self) -> dict:
        analyses = list(self.db[C.RESUME_ANALYSES].find(
            {}, {"ats_score": 1, "confidence": 1, "_id": 0}
        ))
        scores = [doc["ats_score"] for doc in analyses if isinstance(doc.get("ats_score"), (int, float))]
        confidence_scores = [doc["confidence"] for doc in analyses if isinstance(doc.get("confidence"), (int, float))]
        distribution = {"0-49": 0, "50-69": 0, "70-84": 0, "85-100": 0}
        for score in scores:
            key = "0-49" if score < 50 else "50-69" if score < 70 else "70-84" if score < 85 else "85-100"
            distribution[key] += 1
        return {
            "model_version": "resume-analysis-current",
            "total_predictions": len(scores),
            "avg_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else None,
            "prediction_distribution": distribution,
            "feature_importance": {},
        }
